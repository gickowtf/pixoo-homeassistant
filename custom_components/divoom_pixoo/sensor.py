import asyncio
import base64
import hashlib
import logging
import os
import secrets
import shutil
from asyncio import Task
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import requests
import voluptuous as vol
from PIL import Image
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import entity_platform, config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.template import Template, TemplateError
from homeassistant.helpers.network import get_url
from urllib3.exceptions import NewConnectionError

from . import Pixoo
from .pixoo64._colors import get_rgb, CSS4_COLORS, render_color
from .pixoo64._gif import encode_page_gif, extract_frames
from .const import DOMAIN, VERSION
from .pages._pages import special_pages
from .pixoo64._font import FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX, CLOCK, PIX24

_LOGGER = logging.getLogger(__name__)

# Composited pages live in this subdirectory of ``hass.config.path("www")``,
# which Home Assistant serves **without authentication** at ``/local/``.
HOSTED_PAGES_DIRNAME = "pixoo_pages"
HOSTED_PAGE_FILENAME = "page.gif"


def entry_page_prefix(entry_id: str) -> str:
    """The 8 hex chars marking every page folder of one config entry.

    Not a secret: it only has to say who owns a folder, so a new run can sweep
    its own leftovers without looking into another device's page.
    """
    return hashlib.sha256(str(entry_id).encode()).hexdigest()[:8]


def page_folder_name(entry_id: str) -> str:
    """One config entry's page folder for this run: ``<prefix>-<token>``.

    The token is random per setup, and it is the only access control a page has
    (``www/`` is served without authentication): it makes the URL unguessable
    and it retires the previous run's URL before that folder is even swept.
    """
    return f"{entry_page_prefix(entry_id)}-{secrets.token_urlsafe(12)}"


def remove_page_folders(hass: HomeAssistant, entry_id: str) -> None:
    """Delete one entry's page folders. Blocking: call from an executor.

    Only folders carrying the entry's own prefix are removed; another device's
    page - or a ``page.gif`` from an older layout - is never touched. Called at
    setup, because a restart leaves its folder behind (Home Assistant does not
    unload entries on shutdown), and again at unload.
    """
    root = Path(hass.config.path("www")) / HOSTED_PAGES_DIRNAME
    if not root.is_dir():
        return
    prefix = f"{entry_page_prefix(entry_id)}-"
    for folder in root.iterdir():
        if folder.is_dir() and folder.name.startswith(prefix):
            shutil.rmtree(folder, ignore_errors=True)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    entity = Pixoo64(config_entry=config_entry, pixoo=hass.data[DOMAIN][config_entry.entry_id]["pixoo"])
    # Sweep what the previous run left behind: this entity just minted a new
    # folder token, so those folders are already unreachable.
    await hass.async_add_executor_job(remove_page_folders, hass, config_entry.entry_id)
    async_add_entities([entity], True)


class Pixoo64(Entity):

    def __init__(self, pixoo: Pixoo, config_entry: ConfigEntry):
        # self._ip_address = ip_address
        self._pixoo = pixoo
        self._config_entry = config_entry
        self._pages = self._config_entry.options.get('pages_data', [])
        self._scan_interval = timedelta(seconds=int(self._config_entry.options.get('scan_interval', timedelta(seconds=15))))
        self._current_page_index = -1  # Start at -1 so that the first page is 0.
        # Digest of the last composited page played via the hosted-gif path;
        # an unchanged digest means the page is already on screen.
        self._last_hosted_digest: str | None = None
        # This run's page folder (URL sent with every play) and the 8 hex chars
        # that identify our folders in a log line or a directory listing.
        self._page_folder = page_folder_name(self._config_entry.entry_id)
        self._page_prefix = entry_page_prefix(self._config_entry.entry_id)
        self._attr_has_entity_name = True
        self._attr_name = 'Current Page'
        self._attr_extra_state_attributes = {'TotalPages': len(self._pages)}
        _LOGGER.debug("All pages for %s: %s", self._pixoo.address, self._pages)
        self._update_task: None | Task = None
        # One render at a time. Every render job shares this entity's ``Pixoo``
        # (buffer, PicID counter, frame cache, HTTP), and the next page is
        # scheduled before the current render is awaited, so a page whose
        # duration is shorter than a slow push would otherwise start a second
        # render on the same device state.
        self._render_lock = asyncio.Lock()
        # Render caches, reset at the start of every components page render.
        self._image_frame_cache = {}
        self._rendered_component_cache = {}

    async def async_added_to_hass(self):
        platform = entity_platform.async_get_current_platform()
        # Register the buzz service
        platform.async_register_entity_service(
            'play_buzzer',
            {
                vol.Optional('buzz_cycle_time_millis'): cv.positive_int,
                vol.Optional('idle_cycle_time_millis'): cv.positive_int,
                vol.Optional('total_time'): cv.positive_int
            },
            "async_play_buzzer"
        )

        # Register the page service
        platform.async_register_entity_service(
            "show_message",
            {
                vol.Required('page_data'): dict,
                vol.Optional('duration'): cv.positive_int,
            },
            "async_show_message"
        )

        # Register the restart service
        platform.async_register_entity_service(
            'restart',
            {},
            "restart_device"
        )

        # # Register the update page service
        platform.async_register_entity_service(
            'update_page',
            {},
            "update_page"
        )

        await self._async_next_page()

    async def async_will_remove_from_hass(self):
        """When entity is being removed from hass."""
        self.cancel_update_task()
        # Take this run's page folder with us; a folder from an earlier run is
        # swept by the next setup (entry reloads, options updates).
        await self.hass.async_add_executor_job(
            remove_page_folders, self.hass, self._config_entry.entry_id)

    async def async_schedule_next_page(self, wait_time: float):
        _LOGGER.debug("Scheduling next page in %s seconds for %s", wait_time, self._pixoo.address)

        async def task():
            try:
                await asyncio.sleep(wait_time)
                await self._async_next_page()
            except asyncio.CancelledError:
                _LOGGER.debug('Next page timer cancelled for %s', self._pixoo.address)
        # Using HA's async_create_task instead of asyncio.create_task because it's better for HA.
        # (canceled in the async_will_remove_from_hass method of this file)
        self._update_task = self._config_entry.async_create_background_task(self.hass, task(), "pixoo-next-page-timer")

    async def _async_render_page(self, page: dict):
        """Render one page, serialized against every other render.

        The executor job is the unit that owns the shared ``Pixoo``: a push can
        take seconds (32 frames with a pause each), and the page services and
        the page timer all render on the same device. Overlapping renders would
        interleave buffers, the PicID counter and HTTP requests.
        """
        async with self._render_lock:
            await self.hass.async_add_executor_job(self._render_page, page)

    async def _async_next_page(self):
        if self.hass.data[DOMAIN][self._config_entry.entry_id]['available'] is False:
            # The panel is unreachable, so whatever it shows now is not
            # necessarily our composited page (a reboot drops the hosted
            # player): forget the digest and send the page again once it
            # answers.
            self._last_hosted_digest = None
            _LOGGER.debug("Device is not available. Not updating.")
            self.schedule_update_ha_state()
            await self.async_schedule_next_page(self._scan_interval.total_seconds())
            return
        _LOGGER.debug("Loading next page for %s", self._pixoo.address)

        if len(self._pages) == 0:
            return

        is_enabled = None
        iteration_count = 0
        self._current_page_index = (self._current_page_index + 1) % len(self._pages)
        while not is_enabled:
            if iteration_count >= len(self._pages):
                _LOGGER.info("All pages disabled. Not updating.")
                break

            self.page = self._pages[self._current_page_index]

            try:
                is_enabled = str(Template(str(self.page.get('enabled', 'true')), self.hass).async_render())
                is_enabled = is_enabled.lower() in ['true', 'yes', '1', 'on']
            except TemplateError as e:
                _LOGGER.error(f"Error rendering enable template: {e}")
                is_enabled = False

            if is_enabled:
                try:
                    duration = int(Template(str(self.page.get('duration', self._scan_interval.total_seconds())), self.hass).async_render())
                except TemplateError as e:
                    _LOGGER.error("Template render error: %s", e)
                    duration = self._scan_interval.total_seconds()

                await self.async_schedule_next_page(duration)
                self.schedule_update_ha_state()
                try:
                    await self._async_render_page(self.page)
                except:
                    # A send path raised: the panel may be mid-reboot or the
                    # page may be half drawn, so the digest is no longer
                    # trustworthy.
                    self._last_hosted_digest = None
                    _LOGGER.error("Error rendering page for %s. Is the device connected to the network?", self._pixoo.address)
            else:
                self._current_page_index = (self._current_page_index + 1) % len(self._pages)
                iteration_count += 1

    def _render_page(self, page: dict):
        pixoo = self._pixoo
        pixoo.clear()

        page_type = page['page_type'].lower()
        if page_type not in ["custom", "components"]:
            # Stock content (a dial, a channel, a visualizer, a special page, a
            # gif preview) takes the panel off our hosted gif player, so the
            # digest memo - "this composited page is on screen" - stops being
            # true. Forget it, or the next components render of the same bytes
            # is skipped and the panel is left sitting on the stock page.
            self._last_hosted_digest = None
        if page_type in special_pages:
            special_pages[page_type](pixoo, self.hass, page)
            pixoo.push()
        elif page_type == "channel":
            try:
                channel_id = Template(str(page['id']), self.hass).async_render()
            except TemplateError as e:
                _LOGGER.error(f"Error rendering channel id template: {e}")
                channel_id = page['id']
            pixoo.set_custom_page(channel_id)            
        elif page_type == "visualizer":
            try:
                visualizer_id = Template(str(page['id']), self.hass).async_render()
            except TemplateError as e:
                _LOGGER.error(f"Error rendering visualizer id template: {e}")
                visualizer_id = page['id']
            pixoo.set_visualizer(visualizer_id)            
        elif page_type == "clock":
            try:
                clock_id = Template(str(page['id']), self.hass).async_render()
            except TemplateError as e:
                _LOGGER.error(f"Error rendering clock id template: {e}")
                clock_id = page['id']
            pixoo.set_clock(clock_id)
        elif page_type == "gif":
            try:
                gif_url = Template(str(page['gif_url']), self.hass).async_render()
            except TemplateError as e:
                _LOGGER.error(f"Error rendering gif url template: {e}")
                gif_url = page['gif_url']
            pixoo.play_gif(gif_url)
        elif page_type in ["custom", "components"]:
            variables = page.get('variables', {})
            rendered_variables = {}
            for var_name in variables:
                rendered_variables[var_name] = Template(str(variables[var_name]), self.hass).async_render()

            components: list = page['components'].copy()  # Copy the list so we can add new items to it.
            for index, component in enumerate(components):
                if component["type"] == "templatable":
                    try:
                        rendered_list = list(Template(str(component.get("template", [])), self.hass).async_render(variables=rendered_variables))
                        for item in rendered_list[::-1]:  # Reverse the list so that the order is correct.
                            components.insert(index + 1, item)

                    except TemplateError as e:
                        _LOGGER.error("Template render error: %s", e)

            self._render_components(pixoo, components, rendered_variables)

    def _render_components(self, pixoo, components, rendered_variables):
        """Composite the page once per animation frame, then show it.

        Every component replays for each frame, so later components paint over
        earlier ones exactly like a static page. Multi-frame pages are encoded
        as one GIF, served from memory through a short-lived signed URL and
        played via ``Device/PlayTFGif``, so the display never shows the HttpGif
        buffering screen; a failed hosted play falls back to
        :meth:`Pixoo.push_animation`. A page without animated images renders a
        single frame, which is always pushed as pixels.
        """
        # Per render, not per frame: sources and templates may change between
        # renders, but every frame of one page has to show the same content.
        self._image_frame_cache = {}
        self._rendered_component_cache = {}
        frame_count = 1
        pic_speed = None
        for component in components:
            if component.get('type') == "image":
                frames, speed, _ = self._load_image_frames(component, rendered_variables)
                if len(frames) > 1:
                    frame_count = max(frame_count, len(frames))
                    if pic_speed is None:
                        pic_speed = speed
        rendered = []
        for frame_index in range(frame_count):
            pixoo.clear()
            for component in components:
                self._draw_component_frame(pixoo, component, rendered_variables, frame_index)
            rendered.append(pixoo.get_buffer())
        pixoo.clear()
        if len(rendered) > 1:
            self._play_hosted_animation(pixoo, rendered, pic_speed)
            return
        self._push_frames(pixoo, rendered, pic_speed)

    def _push_frames(self, pixoo, rendered, pic_speed):
        """Show ``rendered`` as pushed pixels (the non-hosted path).

        Pushing takes the panel off our hosted gif player, so the memo saying
        "this composited page is on screen" stops being true: forget it, or
        the next render of those same bytes is skipped and the panel is left
        showing something else.
        """
        self._last_hosted_digest = None
        pixoo.push_animation(rendered, pic_speed)

    def _play_hosted_animation(self, pixoo, rendered, pic_speed):
        """Write ``rendered`` as this entry's page gif and play it.

        The page is written to this entry's own folder (see
        :func:`page_folder_name`) and played via ``Device/PlayTFGif``, so the
        display swaps atomically and never shows the HttpGif buffering screen.
        The panel fetches that URL once per play, so an unchanged digest means
        the page is already on screen and no play is sent.

        Falls back to :meth:`Pixoo.push_animation` when hosting or playback
        fails, so the page still animates (with the buffering screen) rather
        than freezing on the previous page.
        """
        if self.hass.state is not CoreState.running:
            # The first rotation tick can fire during platform setup, before
            # Home Assistant's HTTP server answers: the panel then times out on
            # the fetch and refuses connections for ~30 s. hass.is_running is
            # not this test - it is already True while STARTING.
            _LOGGER.debug("Home Assistant is not running yet; pushing frames.")
            self._push_frames(pixoo, rendered, pic_speed)
            return
        try:
            base_url = get_url(self.hass, allow_external=False)
        except Exception as exc:  # misconfigured internal URL
            _LOGGER.warning("Hosted animation unavailable (%s); pushing frames.", exc)
            self._push_frames(pixoo, rendered, pic_speed)
            return
        if base_url.startswith("https://"):
            # Device-side cloud fetch over TLS is unproven; stay on pixels.
            _LOGGER.debug("Hosted animation skipped for https base URL; pushing frames.")
            self._push_frames(pixoo, rendered, pic_speed)
            return
        try:
            blob, digest = encode_page_gif(rendered, pixoo.size, pic_speed)
            dest = (Path(self.hass.config.path("www")) / HOSTED_PAGES_DIRNAME
                    / self._page_folder / HOSTED_PAGE_FILENAME)
            dest.parent.mkdir(parents=True, exist_ok=True)
            # tmp + replace, so a fetch never sees a half-written page.
            tmp = dest.with_name(f".{HOSTED_PAGE_FILENAME}.tmp")
            tmp.write_bytes(blob)
            os.replace(tmp, dest)
            page_url = (f"{base_url}/local/{HOSTED_PAGES_DIRNAME}/"
                        f"{self._page_folder}/{HOSTED_PAGE_FILENAME}")
        except Exception as exc:
            _LOGGER.warning("Hosted animation unavailable (%s); pushing frames.", exc)
            self._push_frames(pixoo, rendered, pic_speed)
            return
        # The folder token is what keeps an unauthenticated page private, so it
        # stays out of the log even at debug; the prefix is enough to tell two
        # devices' folders apart.
        _LOGGER.debug("Hosted page ready: %s/local/%s/%s-.../ (digest %s)",
                      base_url, HOSTED_PAGES_DIRNAME, self._page_prefix, digest)
        if digest == self._last_hosted_digest:
            _LOGGER.debug("Hosted animation unchanged (digest %s); not re-playing.",
                          digest)
            return
        self._last_hosted_digest = digest
        if not pixoo.play_gif(page_url):
            self._push_frames(pixoo, rendered, pic_speed)

    def _load_image_frames(self, component, rendered_variables):
        """Decode an image component into (frames, pic_speed, resample_mode).

        Frames are cached per render: the page is composited once per frame
        index, but the file/URL is only fetched and decoded on the first call.
        Returns ([], None, resample) when the component has no usable source.
        """
        key = id(component)
        if key not in self._image_frame_cache:
            self._image_frame_cache[key] = self._decode_image_frames(component, rendered_variables)
        return self._image_frame_cache[key]

    def _decode_image_frames(self, component, rendered_variables):
        try:
            if "image_path" in component:
                # File
                rendered_image_path = Template(str(component['image_path']), self.hass).async_render(variables=rendered_variables)
                img = Image.open(rendered_image_path)
            elif "image_url" in component:
                # URL/Web
                rendered_image_path = Template(str(component['image_url']), self.hass).async_render(variables=rendered_variables)
                response = requests.get(rendered_image_path, timeout=self._pixoo.timeout)
                img = Image.open(BytesIO(response.content))
            elif "image_data" in component:
                # Base64
                # Use a website like https://base64.guru/converter/encode/image to encode the image.
                rendered_image_data = Template(str(component['image_data']), self.hass).async_render(variables=rendered_variables)
                img = Image.open(BytesIO(base64.b64decode(rendered_image_data)))
            else:
                return [], None, Image.BOX

            # If neither width nor height is set, the image will be displayed in its original size.
            # (If too big, it's handled in the _pixoo class)

            # You can "see" the difference here: https://i.stack.imgur.com/bKlzT.png
            rendered_resample_mode = str(Template(str(component.get('resample_mode', "box")), self.hass).async_render(variables=rendered_variables)).lower()
            if rendered_resample_mode == "nearest" or rendered_resample_mode == "pixel_art":
                resample_mode = Image.NEAREST
            elif rendered_resample_mode == "bilinear":
                resample_mode = Image.BILINEAR
            elif rendered_resample_mode == "hamming":
                resample_mode = Image.HAMMING
            elif rendered_resample_mode == "bicubic":
                resample_mode = Image.BICUBIC
            elif rendered_resample_mode == "antialias" or rendered_resample_mode == "lanczos":
                resample_mode = Image.LANCZOS
            else:
                resample_mode = Image.BOX

            width = component.get('width')
            height = component.get('height')
            try:
                animation_speed = component.get('animation_speed')
                animation_speed = None if animation_speed is None else int(animation_speed)
            except (TypeError, ValueError):
                animation_speed = None

            try:
                img.load()  # fully decode so returned frames survive img.close()
                frames, pic_speed = extract_frames(img, width, height, resample_mode, animation_speed)
            finally:
                try:
                    img.close()
                except Exception:
                    pass
            return frames, pic_speed, resample_mode
        except TemplateError as e:
            _LOGGER.error("Template render error: %s", e)
        except NewConnectionError as e:
            _LOGGER.error("Connection error: %s", e)
        except TimeoutError as e:
            _LOGGER.error("Timeout error: %s", e)
        return [], None, Image.BOX

    def _rendered_text(self, component, rendered_variables):
        """Text and colour of a text component, rendered once per page render.

        Both are templates, and a page is composited once per frame. Evaluating
        them per frame lets a render that straddles a minute boundary bake two
        clock values into one animation (frames 0..k showing one minute, the
        rest the next), which the panel then shows alternating.
        """
        key = id(component)
        if key not in self._rendered_component_cache:
            try:
                rendered_text = str(Template(str(component['content']), self.hass).async_render(variables=rendered_variables))
            except TemplateError as e:
                _LOGGER.error("Template render error: %s", e)
                rendered_text = "Template Error"

            self._rendered_component_cache[key] = (
                rendered_text,
                render_color(component.get('color'), self.hass, variables=rendered_variables),
            )
        return self._rendered_component_cache[key]

    def _draw_text_component(self, pixoo, component, rendered_variables):
        rendered_text, rendered_color = self._rendered_text(component, rendered_variables)

        font_name = component.get('font', "").lower()
        if font_name == "gicko":
            font = FONT_GICKO
        elif font_name == "five_pix":
            font = FIVE_PIX
        elif font_name == "eleven_pix":
            font = ELEVEN_PIX
        elif font_name == "clock":
            font = CLOCK
        elif font_name == "pix24":
            font = PIX24
        else:
            font = FONT_PICO_8  # Font by default.

        align = component.get('align', "").lower()

        pixoo.draw_text(rendered_text.upper(), tuple(component['position']), rendered_color, font, align)

    def _rendered_rectangle(self, component, rendered_variables):
        """Colour, geometry and fill flag of a rectangle, once per page render.

        Cached for the same reason as :meth:`_rendered_text`: these are
        templates, and every frame of one page has to agree on them. Returns
        None when a template fails, in which case nothing is drawn.
        """
        key = id(component)
        if key not in self._rendered_component_cache:
            try:
                rendered_color = render_color(component.get('color'), self.hass, variables=rendered_variables)

                position = [
                    int(Template(str(position), self.hass).async_render(variables=rendered_variables)) for position in
                    component['position']
                ]
                size = [
                    int(Template(str(size), self.hass).async_render(variables=rendered_variables)) for size in
                    component['size']
                ]

                size = (size[0] - 1, size[1] - 1)

                rendered_fill = bool(Template(str(component.get('filled', True)), self.hass).async_render(variables=rendered_variables))

                self._rendered_component_cache[key] = (rendered_color, position, size, rendered_fill)
            except TemplateError as e:
                _LOGGER.error("Template render error: %s", e)
                self._rendered_component_cache[key] = None
        return self._rendered_component_cache[key]

    def _draw_rectangle_component(self, pixoo, component, rendered_variables):
        rendered = self._rendered_rectangle(component, rendered_variables)
        if rendered is None:
            return
        rendered_color, position, size, rendered_fill = rendered

        if rendered_fill:
            pixoo.draw_filled_rectangle(position, (position[0] + size[0], position[1] + size[1]), rendered_color)
        else:
            pixoo.draw_line(position, (position[0] + size[0], position[1]), rendered_color)
            pixoo.draw_line((position[0] + size[0], position[1]), (position[0] + size[0], position[1] + size[1]), rendered_color)
            pixoo.draw_line((position[0] + size[0], position[1] + size[1]), (position[0], position[1] + size[1]), rendered_color)
            pixoo.draw_line((position[0], position[1] + size[1]), position, rendered_color)

    def _draw_component_frame(self, pixoo, component, rendered_variables, frame_index):
        """Draw one component for animation frame N (static layers ignore N)."""
        component_type = component.get('type')
        if component_type == "text":
            self._draw_text_component(pixoo, component, rendered_variables)
        elif component_type == "rectangle":
            self._draw_rectangle_component(pixoo, component, rendered_variables)
        elif component_type == "image":
            frames, _, resample_mode = self._load_image_frames(component, rendered_variables)
            if not frames:
                return
            pixoo.draw_image(frames[frame_index % len(frames)], tuple(component['position']),
                             image_resample_mode=resample_mode)

    # Service to show a message.
    async def async_show_message(self, page_data: dict, duration: int = -1):
        duration = timedelta(seconds=duration if duration >= 0 else self._scan_interval.total_seconds())

        if not page_data or not page_data.get('page_type'):
            _LOGGER.error("No page to render.")
            return

        await self._async_render_page(page_data)
        if self._update_task:
            self.cancel_update_task()
            await self.async_schedule_next_page(duration.total_seconds())

    # Service to play the buzzer
    async def async_play_buzzer(self, buzz_cycle_time_millis: int = 500, idle_cycle_time_millis: int = 500, total_time: int = 3000):
        def buzz():
            self._pixoo.play_buzzer(timedelta(milliseconds=buzz_cycle_time_millis), timedelta(milliseconds=idle_cycle_time_millis), timedelta(milliseconds=total_time))

        await self.hass.async_add_executor_job(buzz)

    async def restart_device(self):
        def restart():
            self._pixoo.restart_device()

        await self.hass.async_add_executor_job(restart)

    async def update_page(self):
        await self._async_render_page(self.page)

    def cancel_update_task(self):
        if self._update_task:
            self._update_task.cancel()
            _LOGGER.debug("Successfully canceled update task for %s", self._pixoo.address)

    @property
    def state(self):
        return self._current_page_index+1

    @property
    def available(self) -> bool | None:
        return self.hass.data[DOMAIN][self._config_entry.entry_id]['available']

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._config_entry.entry_id)) if self._config_entry is not None else (DOMAIN, "divoom")},
            name=self._config_entry.title,
            manufacturer="Divoom",
            model="Pixoo",
            sw_version=VERSION,
        )

    @property
    def unique_id(self):
        return "current_page_" + str(self._config_entry.entry_id)

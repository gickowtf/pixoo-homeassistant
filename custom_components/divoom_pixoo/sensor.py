import asyncio
import base64
import logging
from datetime import timedelta, datetime
from io import BytesIO

import requests
import voluptuous as vol
from PIL import Image
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.template import Template, TemplateError
from urllib3.exceptions import NewConnectionError

from .pixoo64._colors import get_rgb, CSS4_COLORS, render_color
from .const import DOMAIN, VERSION
from .pages._pages import special_pages
from .pixoo64._font import FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX, CLOCK


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    async_add_entities([ Pixoo64(config_entry=config_entry, pixoo=hass.data[DOMAIN][config_entry.entry_id]["pixoo"]) ], True)


class Pixoo64(Entity):

    def __init__(self, pages="", scan_interval=timedelta(seconds=15), pixoo=None, config_entry=None):
        # self._ip_address = ip_address
        self._pixoo = pixoo
        self._config_entry = config_entry
        self._pages = self._config_entry.options.get('pages_data', pages)
        self._scan_interval = timedelta(seconds=int(self._config_entry.options.get('scan_interval', scan_interval)))
        self._current_page_index = -1  # Start at -1 so that the first page is 0.
        self._current_page = None
        self._attr_has_entity_name = True
        self._attr_name = 'Current Page'
        self._attr_extra_state_attributes = {'TotalPages': len(self._pages)}
        _LOGGER.debug("All pages for %s: %s", self._pixoo.address, self._pages)
        self._notification_before = datetime.now()

    async def async_added_to_hass(self):
        # Register the buzz service
        self.hass.services.async_register(
            DOMAIN,
            'play_buzzer',
            self.async_play_buzzer,
            schema=vol.Schema({
                vol.Optional('buzz_cycle_time_millis'): int,
                vol.Optional('idle_cycle_time_millis'): int,
                vol.Optional('total_time'): int
            }, extra=vol.ALLOW_EXTRA)
        )

        # Register the page service
        self.hass.services.async_register(
            DOMAIN,
            'show_message',
            self.async_show_message,
            schema=vol.Schema({
                vol.Required('page_data'): dict,
                vol.Optional('duration'): int,
            }, extra=vol.ALLOW_EXTRA)
        )

        # Register the restart service
        self.hass.services.async_register(
            DOMAIN,
            'restart',
            self.restart_device,
            schema=vol.Schema({}, extra=vol.ALLOW_EXTRA)
        )
        # Continue with the setup
        if DOMAIN in self.hass.data:
            self.hass.data[DOMAIN].setdefault('entities', []).append(self)
        self._update_interval = async_track_time_interval(
            self.hass,
            self._async_update,
            self._scan_interval
        )
        await self._async_update()

    async def async_will_remove_from_hass(self):
        """When entity is being removed from hass."""
        if self._update_interval is not None:
            self._update_interval()
            self._update_interval = None

    async def _async_update(self, now=None):
        _LOGGER.debug("Update called at %s for %s", now, self._pixoo.address)
        await self._async_next_page()

    async def _async_next_page(self):
        if self._notification_before > datetime.now():
            return

        if len(self._pages) == 0:
            return

        is_enabled = None
        iteration_count = 0
        self._current_page_index = (self._current_page_index + 1) % len(self._pages)  # Increment the page index, duh.
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
                self.schedule_update_ha_state()
                await self.hass.async_add_executor_job(self._render_page, self.page)
            else:
                self._current_page_index = (self._current_page_index + 1) % len(self._pages)
                iteration_count += 1

    def _render_page(self, page):
        pixoo = self._pixoo
        pixoo.clear()

        page_type = page['page_type'].lower()
        if page_type in special_pages:
            special_pages[page_type](pixoo, self.hass, page)
            pixoo.push()
        elif page_type == "channel":
            pixoo.set_custom_page(page['id'])
        elif page_type == "visualizer":
            pixoo.set_visualizer(page['id'])
        elif page_type == "clock":
            pixoo.set_clock(page['id'])
        elif page_type in ["custom", "components"]:
            for component in page['components']:

                if component['type'] == "text":
                    text_template = Template(str(component['content']), self.hass)
                    try:
                        rendered_text = str(text_template.async_render())
                    except TemplateError as e:
                        _LOGGER.error("Template render error: %s", e)
                        rendered_text = "Template Error"

                    font = FONT_PICO_8  # Font by default.
                    if component['font'] == "PICO_8":
                        font = FONT_PICO_8
                    elif component['font'] == "GICKO":
                        font = FONT_GICKO
                    elif component['font'] == "FIVE_PIX":
                        font = FIVE_PIX

                    rendered_color = render_color(component['color'], self.hass)

                    pixoo.draw_text(rendered_text.upper(), tuple(component['position']), rendered_color, font)

                elif component['type'] == "image":
                    try:
                        if "image_path" in component:
                            # File
                            rendered_image_path = Template(str(component['image_path']), self.hass).async_render()
                            img = Image.open(rendered_image_path)
                        elif "image_url" in component:
                            # URL/Web
                            rendered_image_path = Template(str(component['image_url']), self.hass).async_render()
                            response = requests.get(rendered_image_path, timeout=pixoo.timeout)
                            img = Image.open(BytesIO(response.content))
                        elif "image_data" in component:
                            # Base64
                            # Use a website like https://base64.guru/converter/encode/image to encode the image.
                            rendered_image_data = Template(str(component['image_data']), self.hass).async_render()
                            img = Image.open(BytesIO(base64.b64decode(rendered_image_data)))
                        else:
                            continue

                        # If neither width nor height is set, the image will be displayed in its original size.
                        # (If too big, it's handled in the _pixoo class)

                        # You can "see" the difference here: https://i.stack.imgur.com/bKlzT.png
                        rendered_resample_mode = str(Template(str(component.get('resample_mode', "box")), self.hass).async_render()).lower()
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

                        if width and height:
                            img = img.resize((width, height), resample_mode)
                        elif width or height:
                            img.thumbnail((100 if not width else width, 100 if not height else height), resample_mode)

                        pixoo.draw_image(img, tuple(component['position']), image_resample_mode=resample_mode)
                    except TemplateError as e:
                        _LOGGER.error("Template render error: %s", e)
                    except NewConnectionError as e:
                        _LOGGER.error("Connection error: %s", e)
                    except TimeoutError as e:
                        _LOGGER.error("Timeout error: %s", e)

            pixoo.push()

    # Service to show a message.
    # Comment: By calling this, it's possible that next_page "skips" a page, therefore looking like a next page takes
    # longer than normal. I'm not 100% certain on how to make this work properly...
    async def async_show_message(self, call):
        page_data = call.data.get('page_data')
        duration = timedelta(seconds=call.data.get('duration', self._scan_interval.seconds))

        if not page_data or not page_data.get('page_type'):
            _LOGGER.error("No page to render.")
            return

        def draw():
            self._render_page(page_data)

        await self.hass.async_add_executor_job(draw)
        self._notification_before = datetime.now() + duration
    #     By not using the sleep method, HA will show a success thingy in the UI.
    #     If not, the success will only appear after the sleep time.

    # Service to play the buzzer
    async def async_play_buzzer(self, call):
        buzz_cycle_time = timedelta(milliseconds=call.data.get('buzz_cycle_time_millis', 500))
        idle_cycle_time = timedelta(milliseconds=call.data.get('idle_cycle_time_millis', 500))
        total_time = timedelta(milliseconds=call.data.get('total_time', 3000))

        def buzz():
            self._pixoo.play_buzzer(buzz_cycle_time, idle_cycle_time, total_time)

        await self.hass.async_add_executor_job(buzz)

    async def restart_device(self, call):
        def restart():
            self._pixoo.restart_device()

        await self.hass.async_add_executor_job(restart)

    @property
    def state(self):
        return self._current_page_index+1

    @property
    def entity_category(self):
        return EntityCategory.DIAGNOSTIC


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
import asyncio
import voluptuous as vol
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
from homeassistant.helpers import config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers.template import Template, TemplateError
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from . import DOMAIN
from .schemas.page_schema import PAGE_SCHEMA

from .pages.solar import solar

from .pixoo64._pixoo import Pixoo
from .pixoo64._font import FONT_PICO_8, FONT_GICKO

import logging

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional('scan_interval'): cv.time_period,
    vol.Required('pages'): vol.All(cv.ensure_list, [PAGE_SCHEMA]),
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        discovery_info = config.get(DOMAIN)
    if discovery_info is None:
        return
    ip_address = discovery_info[CONF_IP_ADDRESS]
    pages = discovery_info.get('pages', [])
    for page in pages:
        condition_template = page.get('condition')
        if condition_template is not None:
            try:
                page['condition_template'] = Template(condition_template, hass)
            except (TemplateError, ValueError) as e:
                _LOGGER.error("Error in condition template: %s", e)
                page['condition_template'] = None

    scan_interval_config = discovery_info.get('scan_interval')
    _LOGGER.debug("Scan interval config: %s", scan_interval_config)
    if isinstance(scan_interval_config, dict):
        scan_interval = timedelta(**scan_interval_config)
    elif scan_interval_config is not None:
        scan_interval = timedelta(seconds=int(scan_interval_config))
    else:
        _LOGGER.error("Scan interval is not defined, falling back to default of 30 seconds.")
        scan_interval = timedelta(seconds=30)
    _LOGGER.debug("Scan interval config: %s", scan_interval_config)
    _LOGGER.debug("Scan interval: %s", scan_interval)

    entity = Pixoo64(ip_address, pages, scan_interval)
    async_add_entities([entity], True)

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        'show_message',
        {
            vol.Required('messages'): [cv.string],
            vol.Required('positions'): [[cv.positive_int]],
            vol.Required('colors'): [[cv.positive_int]],
            vol.Required('fonts'): [cv.string],
            vol.Optional('images', default=[]): [cv.string],
            vol.Optional('image_positions', default=[]): [[cv.positive_int]],
        },
        'async_show_message',
    )


class Pixoo64(Entity):

    def __init__(self, ip_address, pages, scan_interval):
        self._ip_address = ip_address
        self._pages = pages
        self._scan_interval = scan_interval
        self._current_page_index = 0
        self._current_page = self._pages[self._current_page_index]
        self._attr_name = 'divoom_pixoo'
        self._attr_extra_state_attributes = {}
        self._attr_extra_state_attributes['page'] = self._current_page['page']
        _LOGGER.debug(pages)
        self.showing_notification = False

    async def async_added_to_hass(self):
        if DOMAIN in self.hass.data:
            self.hass.data[DOMAIN].setdefault('entities', []).append(self)
        self._update_interval = async_track_time_interval(
            self.hass,
            self._async_update,
            self._scan_interval
        )

    async def async_will_remove_from_hass(self):
        """When entity is being removed from hass."""
        if self._update_interval is not None:
            self._update_interval()
            self._update_interval = None

    async def _async_update(self, now=None):
        _LOGGER.debug("Update called at %s", now)
        await self._async_update_data()

    async def _async_update_data(self):
        if self.showing_notification:
            return

        self._current_page = self._pages[self._current_page_index]
        current_page_data = self._pages[self._current_page_index]
        _LOGGER.debug(f"current page: {current_page_data}")
        self._attr_extra_state_attributes['page'] = current_page_data['page']


        if 'condition_template' in current_page_data:
            condition = current_page_data['condition_template']
            condition.hass = self.hass
            try:
                if not condition.async_render():
                    self._current_page_index = (self._current_page_index + 1) % len(self._pages)
                    return
            except TemplateError as e:
                _LOGGER.error("Error rendering condition template: %s", e)
                self._current_page_index = (self._current_page_index + 1) % len(self._pages)
                return


        def update():
            pixoo = Pixoo(self._ip_address)
            pixoo.clear()

            if "channel" in current_page_data:
                for ch in current_page_data["channel"]:
                    pixoo.set_custom_page(ch['number'])

            if "clockId" in current_page_data:
                for clock in current_page_data["clockId"]:
                    pixoo.set_clock(clock['number'])

            if "images" in current_page_data:
                for image in current_page_data["images"]:
                    pixoo.draw_image(image['image'], tuple(image['position']))
                pixoo.push()

            if "texts" in current_page_data:
                for text in current_page_data["texts"]:
                    text_template = Template(text['text'], self.hass)
                    try:
                        rendered_text = str(text_template.async_render())
                    except TemplateError as e:
                        _LOGGER.error("Template render error: %s", e)
                        rendered_text = "Template Error"

                    if text['font'] == "FONT_PICO_8":
                        pixoo.draw_text(rendered_text, tuple(text['position']), tuple(text['font_color']), FONT_PICO_8)
                    if text['font'] == "FONT_GICKO":
                        pixoo.draw_text(rendered_text.upper(), tuple(text['position']), tuple(text['font_color']), FONT_GICKO)
                pixoo.push()

            if "PV" in current_page_data:
                solar(pixoo, self.hass, current_page_data, FONT_PICO_8, FONT_GICKO)
                pixoo.push()

        await self.hass.async_add_executor_job(update)
        self._current_page_index = (self._current_page_index + 1) % len(self._pages)



    async def async_show_message(self, messages, positions, colors, fonts, images=None, image_positions=None):
        if not all([messages, positions, colors, fonts]) or len(messages) != len(positions) != len(colors) != len(fonts):
            _LOGGER.error("Lists for messages, positions, colors, and fonts must all be present and have the same length.")
            return

        self.showing_notification = True

        def draw():
            pixoo = Pixoo(self._ip_address)
            pixoo.clear()

            for img, img_pos in zip(images, image_positions):
                pixoo.draw_image(img, tuple(img_pos))

            for message, position, color, font in zip(messages, positions, colors, fonts):
                selected_font = FONT_PICO_8 if font == 'FONT_PICO_8' else FONT_GICKO
                if font == 'FONT_PICO_8':
                    pixoo.draw_text(message, tuple(position), tuple(color), selected_font)
                else:
                    pixoo.draw_text(message.upper(), tuple(position), tuple(color), selected_font)

            pixoo.push()

        await self.hass.async_add_executor_job(draw)
        await asyncio.sleep(self._scan_interval.total_seconds())
        self.showing_notification = False


    @property
    def state(self):
        return self._current_page['page']

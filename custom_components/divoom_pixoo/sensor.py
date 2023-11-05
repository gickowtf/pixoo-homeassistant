import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity

from custom_components.divoom_pixoo.pixoo64._pixoo import \
    Pixoo

from custom_components.divoom_pixoo.pixoo64._font import \
    FONT_PICO_8, FONT_GICKO

DOMAIN = "divoom_pixoo"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required('ip_address'): cv.string,
    vol.Required('pages'): vol.All(cv.ensure_list, [
        vol.Schema({
            vol.Required('page'): cv.positive_int,
            vol.Optional('texts'): vol.All(cv.ensure_list, [
                vol.Schema({
                    vol.Required('text'): cv.string,
                    vol.Required('position'): vol.All(cv.ensure_list, [cv.positive_int], vol.Length(min=2, max=2)),
                    vol.Required('font'): cv.string,
                    vol.Required('font_color'): vol.All(cv.ensure_list, [cv.positive_int], vol.Length(min=3, max=3)),
                })
            ]),
            vol.Optional('images'): vol.All(cv.ensure_list, [
                vol.Schema({
                    vol.Required('image'): cv.string,
                    vol.Required('position'): vol.All(cv.ensure_list, [cv.positive_int], vol.Length(min=2, max=2)),
                })
            ]),
        })
    ]),
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    ip_address = config.get('ip_address')
    pages = config.get('pages')
    add_entities([Pixoo64(ip_address, pages)])


class Pixoo64(Entity):
    def __init__(self, ip_address, pages):
        self._ip_address = ip_address
        self._pages = pages
        self._current_page_index = 0
        self._current_page = self._pages[self._current_page_index]
        self._attr_name = 'divoom_pixoo'
        self._attr_extra_state_attributes = {}
        self._attr_extra_state_attributes['list'] = pages

    def update(self):
        self._current_page = self._pages[self._current_page_index]
        self._current_page_index = (self._current_page_index + 1) % len(self._pages)
        green = (99, 199, 77)
        pixoo = Pixoo(self._ip_address)
        pixoo.clear()

        for image in self._pages[self._current_page_index].get("images", []):
            img = image['image']
            posX = image['position'][0]
            posY = image['position'][1]
            pixoo.draw_image(img, (posX, posY))

        for text in self._attr_extra_state_attributes['list'][self._current_page_index]["texts"]:
            font = text['font']
            posX = text['position'][0]
            posY = text['position'][1]
            rgbR = text['font_color'][0]
            rgbG = text['font_color'][1]
            rgbB = text['font_color'][2]

            if "sensor." in text["text"]:
                texts = text["text"]
                splittedtext = texts.split()
                for i in range(len(splittedtext)):
                    if "sensor." in splittedtext[i]:
                        splittedtext[i] = str(self.hass.states.get(splittedtext[i]).state)
                text = " ".join(splittedtext)
            else:
                text = str(text['text'])

            if font == "FONT_PICO_8":
                pixoo.draw_text(text, (posX, posY), (rgbR, rgbG, rgbB), FONT_PICO_8)
            if font == "FONT_GICKO":
                pixoo.draw_text(text, (posX, posY), (rgbR, rgbG, rgbB), FONT_GICKO)

        pixoo.push()


    @property
    def state(self):
        return self._current_page['page']



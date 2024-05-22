from homeassistant.components.light import (LightEntity, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, ColorMode)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from . import DOMAIN, VERSION

from .pixoo64._pixoo import Pixoo
import logging

_LOGGER = logging.getLogger(__name__)
BRIGHTNESS_SCALE = (1, 100)


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):
    async_add_entities([ DivoomLight(config_entry=config_entry, pixoo=hass.data[DOMAIN][config_entry.entry_id]["pixoo"]) ], True)


class DivoomLight(LightEntity):
    def __init__(self, ip_address=None, config_entry: ConfigEntry = None, pixoo: Pixoo = None):
        self._ip_address = ip_address
        self._config_entry = config_entry
        self._attr_has_entity_name = True
        self._name = "Light"
        self._pixoo = Pixoo(self._ip_address) if pixoo is None else pixoo
        self._brightness = None
        self._state = None
        _LOGGER.debug(f"Divoom Pixoo IP address from configuration: {self._ip_address}")

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self) -> bool | None:
        return self._state

    @property
    def brightness(self):
        return self._brightness

    def turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            brightness_percent = int((self._brightness / 255.0) * 100)
            self._pixoo.set_brightness(brightness_percent)
        self._state = True
        self._pixoo.set_screen(True)

    def turn_off(self, **kwargs):
        self._state = False
        self._pixoo.set_screen(False)

    def update(self) -> None:
        try:
            self._state = self._pixoo.get_state()
            brightness_percent = self._pixoo.get_brightness()
            self._brightness = int((brightness_percent / 100.0) * 255)
            self.hass.data[DOMAIN][self._config_entry.entry_id]['available'] = True
        except:
            self.hass.data[DOMAIN][self._config_entry.entry_id]['available'] = False

    @property
    def available(self) -> bool | None:
        return self.hass.data[DOMAIN][self._config_entry.entry_id]['available']

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        return {ColorMode.BRIGHTNESS}

    @property
    def unique_id(self):
        return "light_" + str(self._config_entry.entry_id)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._config_entry.entry_id)) if self._config_entry is not None else (DOMAIN, "divoom")},
            name=self._config_entry.title,
            manufacturer="Divoom",
            model="Pixoo",
            sw_version=VERSION,
        )

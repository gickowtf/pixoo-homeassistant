from homeassistant.components.light import (LightEntity, ATTR_BRIGHTNESS, ColorMode)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util.color import brightness_to_value, value_to_brightness

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

    def turn_on(self, **kwargs):
        self._state = True
        self._pixoo.set_screen(True)
        if ATTR_BRIGHTNESS in kwargs:
            val = brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS])
            self._pixoo.set_brightness(val)

    def turn_off(self, **kwargs):
        self._state = False
        self._pixoo.set_screen(False)

    def update(self) -> None:
        self._state = self._pixoo.get_state()
        self._brightness = value_to_brightness(BRIGHTNESS_SCALE, self._pixoo.get_brightness())

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

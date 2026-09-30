from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from . import DOMAIN, VERSION

from .pixoo64._pixoo import Pixoo
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):
    async_add_entities([ DivoomLight(config_entry=config_entry, pixoo=hass.data[DOMAIN][config_entry.entry_id]["pixoo"]) ], True)


class DivoomLight(LightEntity):
    def __init__(self, ip_address=None, config_entry: ConfigEntry = None, pixoo: Pixoo = None):
        self._ip_address = ip_address
        self._config_entry = config_entry
        self._attr_has_entity_name = True
        self._name = "Light"
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._pixoo = Pixoo(self._ip_address) if pixoo is None else pixoo
        self._brightness = None
        self._state = None
        self._available = True
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
        self._set_on_with_kwargs(kwargs)

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self._set_on_with_kwargs, kwargs)

    def _set_on_with_kwargs(self, kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            brightness_percent = int((self._brightness / 255.0) * 100)
            self._pixoo.set_brightness(brightness_percent)
        self._state = True
        self._pixoo.set_screen(True)

    def turn_off(self, **kwargs):
        self._set_off()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._set_off)

    def _set_off(self):
        self._state = False
        self._pixoo.set_screen(False)

    def update(self) -> None:
        self._update_state()

    async def async_update(self):
        await self.hass.async_add_executor_job(self._update_state)

    def _update_state(self) -> None:
        try:
            self._state = self._pixoo.get_state()
            brightness_percent = self._pixoo.get_brightness()
            self._brightness = int((brightness_percent / 100.0) * 255)
            self._set_available(True)
        except Exception as err:
            _LOGGER.debug("Unable to update light state: %s", err)
            self._set_available(False)

    def _set_available(self, value: bool) -> None:
        self._available = value
        if self.hass is not None and self._config_entry is not None:
            self.hass.data[DOMAIN][self._config_entry.entry_id]['available'] = value

    @property
    def available(self) -> bool | None:
        if self.hass is not None and self._config_entry is not None:
            return self.hass.data[DOMAIN][self._config_entry.entry_id]['available']
        return self._available

    @property
    def unique_id(self):
        if self._config_entry is None:
            return "light_divoom"
        return "light_" + str(self._config_entry.entry_id)

    @property
    def device_info(self) -> DeviceInfo:
        entry_id = str(self._config_entry.entry_id) if self._config_entry is not None else "divoom"
        name = self._config_entry.title if self._config_entry is not None else "Divoom Pixoo"
        return DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=name,
            manufacturer="Divoom",
            model="Pixoo",
            sw_version=VERSION,
        )

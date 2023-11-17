import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (ATTR_BRIGHTNESS, PLATFORM_SCHEMA, LightEntity)
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from . import DOMAIN, VERSION

from .pixoo64._pixoo import Pixoo
import logging

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    })

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Awesome Light platform."""
    if discovery_info is None:
        _LOGGER.error("No discovery_info found in Divoom Pixoo light setup")
        return
    ip_address = discovery_info.get(CONF_IP_ADDRESS)
    if ip_address is None:
        _LOGGER.error("No IP address found for Divoom Pixoo light")
        return

    light = DivoomLight(ip_address)
    add_entities([light], True)


class DivoomLight(LightEntity):
    def __init__(self, ip_address):
        self._ip_address = ip_address
        self._name = "Divoom Pixoo 64 Light"
        self._state = None
        self._brightness = None
        self._pixoo = Pixoo(self._ip_address)
        _LOGGER.debug(f"Divoom Pixoo IP address from configuration: {self._ip_address}")

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        return self._brightness

    @property
    def is_on(self) -> bool | None:
        return self._state


    def turn_on(self, **kwargs):
        self._state = True
        self._pixoo.set_screen(True)

    def turn_off(self, **kwargs):
        self._state = False
        self._pixoo.set_screen(False)


    def update(self) -> None:
        self._state = self._pixoo.get_state()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"divoom_pixoo_light"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            manufacturer="Divoom",
            model="Pixoo",
            sw_version=VERSION,
        )

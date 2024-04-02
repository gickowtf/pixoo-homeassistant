import requests
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.helpers.selector import ObjectSelector, ObjectSelectorConfig, TextSelector, TextSelectorConfig, \
    DurationSelector, DurationSelectorConfig, NumberSelector, NumberSelectorConfig, NumberSelectorMode, SelectSelector, \
    SelectSelectorConfig, SelectSelectorMode

from .const import DOMAIN, CURRENT_ENTRY_VERSION
import voluptuous as vol
from . import load_pixoo

import logging

_LOGGER = logging.getLogger(__name__)


def get_lan_devices():
    return requests.get("https://app.divoom-gz.com/Device/ReturnSameLANDevice", timeout=5).json()


class ConfigFlowHandler(config_entries.ConfigFlow, config_entries.OptionsFlow, domain=DOMAIN):
    VERSION = CURRENT_ENTRY_VERSION  # Version for new entries. Managed by HA

    def __init__(self, config_entry: ConfigEntry = None):
        self.entry_options = config_entry.options if config_entry else {"ip_address": "", "scan_interval": "15",
                                                                        "pages_data": [{'page_type': 'PV', 'power': '{{ states.sensor.YOUR_SENSOR.state }}', 'storage': '{{ states.sensor.YOUR_SENSOR.state }}', 'discharge': '{{ states.sensor.YOUR_SENSOR.state }}', 'powerhousetotal': '{{ states.sensor.YOUR_SENSOR.state }}', 'vomNetz': '{{ states.sensor.YOUR_SENSOR.state }}', 'time': "{{ now().strftime('%H:%M') }}"}, {'page_type': 'components', 'components': [{'type': 'text', 'content': 'github/gickowtf', 'position': [0, 10], 'font': 'PICO_8', 'color': [255, 0, 0]}, {'type': 'text', 'content': 'Thx 4 Support', 'position': [0, 30], 'font': 'PICO_8', 'color': [255, 0, 0]}, {'type': 'image', 'image_path': '/config/custom_components/divoom_pixoo/img/haus.png', 'position': [30, 10]}]}, {'page_type': 'channel', 'id': 2}, {'page_type': 'clock', 'id': 39}]}

    async def async_step_user(self, user_input: dict = None):
        # Called when the user creates a new entry. This will open a page with discovered new devices if there's any.
        if user_input:
            return await self.async_step_config({"ip_address": user_input["selector"] if not user_input["selector"] == "manual" else "", "dont_test": True})

        try:
            response = await self.hass.async_add_executor_job(get_lan_devices)
            _LOGGER.debug("Discovery data: %s", response)

            devices = []
            for device in response["DeviceList"]:
                if await self.verify_unique_device(device["DevicePrivateIP"]):
                    devices.append({"value": device["DevicePrivateIP"], "label": device["DeviceName"] + " (" + device["DevicePrivateIP"] + ")"})

            if len(devices) == 0:
                # No new device was found, manual config
                return await self.async_step_config()

            devices.append({"value": "manual", "label": "Manual IP"})

            return self.async_show_form(
                step_id="user", data_schema=vol.Schema({
                    vol.Required("selector"): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            options=devices,
                            multiple=False,

                        )
                    )
                })
            )

        except Exception as e:
            _LOGGER.error(e)
        return await self.async_step_config()

    async def async_step_config(self, user_input: dict = None):
        errors = {}
        if user_input is not None and not user_input.get("dont_test", False):
            try:
                pix = await self.hass.async_add_executor_job(load_pixoo, user_input.get('ip_address'))
                if await self.verify_unique_device(user_input.get('ip_address')):
                    # TODO: Add config verification
                    return self.async_create_entry(title="Divoom Pixoo 64", data=user_input,
                                                   options=user_input)  # it's required to set
                # data anyways since otherwise the option flow won't save the data. (HA bug?) PS: DATA ISN'T USED HERE.
                else:
                    errors["ip_address"] = "already_configured"
            except Exception as e:
                _LOGGER.error("Error setting up Pixoo: %s", e)
                errors["ip_address"] = "connection"
        else:
            user_input = {} if user_input is None else user_input

        return self.async_show_form(
            step_id="config", errors=errors, data_schema=vol.Schema({
                vol.Required("ip_address",
                             default=user_input.get("ip_address", self.entry_options.get("ip_address"))): str,
                vol.Required("scan_interval", default=user_input.get("scan_interval", self.entry_options.get(
                    "scan_interval"))): NumberSelector(
                    NumberSelectorConfig(min=1, max=9999, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="seconds")
                ),
                vol.Optional("pages_data",
                             default=user_input.get("pages_data",
                                                    self.entry_options.get("pages_data"))): ObjectSelector(
                    ObjectSelectorConfig()

                )
            })
        )

    # Gives the OptionsFlow class to HA
    def async_get_options_flow(config_entry):
        return ConfigFlowHandler(config_entry)

    async def async_step_init(self, user_input=None):
        # This is set since the Option Flow's first step is always init.
        return await self.async_step_config(user_input)

    async def verify_unique_device(self, ip_address: str):
        """Check if the device is already configured."""

        # return True #DEBUG
        if ip_address == self.entry_options.get("ip_address"):  # If the user didn't change the IP, it's still valid.
            return True

        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.options['ip_address'] == ip_address:
                return False
        return True

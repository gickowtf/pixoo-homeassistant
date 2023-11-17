# __init__.py
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import discovery
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

DOMAIN = "divoom_pixoo"
VERSION = "1.2.0"


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Divoom Pixoo component from configuration.yaml."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    hass.data[DOMAIN] = {
        'ip_address': conf['ip_address'],
        'entities': []
    }

    hass.async_create_task(
        discovery.async_load_platform(hass, 'sensor', DOMAIN, conf, config)
    )

    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            'light',
            DOMAIN,
            {'ip_address': conf['ip_address']},
            config
        )
    )

    async def async_show_message(service: ServiceCall):
        """Handle the service call to show a message on the Pixoo device."""
        entity_id = service.data.get('entity_id')
        messages = service.data.get('messages')
        positions = service.data.get('positions')
        colors = service.data.get('colors')
        fonts = service.data.get('fonts')
        images = service.data.get('images', [])
        image_positions = service.data.get('image_positions', [])
        ...
        for entity in hass.data[DOMAIN].get('entities', []):
            if entity.entity_id == entity_id:
                await entity.async_show_message(messages, positions, colors, fonts, images, image_positions)
                break

    # Service registrieren
    hass.services.async_register(DOMAIN, 'show_message', async_show_message)

    return True

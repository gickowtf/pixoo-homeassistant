# __init__.py
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import discovery
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

DOMAIN = "divoom_pixoo"


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
        message = service.data.get('message')
        position = service.data.get('position')
        color = service.data.get('color')
        font = service.data.get('font')
        image = service.data.get('image')
        image_position = service.data.get('image_position')

        for entity in hass.data[DOMAIN].get('entities', []):
            if entity.entity_id == entity_id:
                await entity.async_show_message(message, position, color, font, image, image_position)
                break

    # Service registrieren
    hass.services.async_register(DOMAIN, 'show_message', async_show_message)

    return True

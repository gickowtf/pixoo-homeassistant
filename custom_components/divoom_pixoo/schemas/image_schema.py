import voluptuous as vol
from homeassistant.helpers import config_validation as cv

IMAGE_SCHEMA = vol.Schema({
    vol.Required('image'): cv.string,
    vol.Required('position'): vol.All(cv.ensure_list, [cv.positive_int], vol.Length(min=2, max=2)),
})

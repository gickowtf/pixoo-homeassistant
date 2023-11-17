import voluptuous as vol
from homeassistant.helpers import config_validation as cv

CLOCKID_SCHEMA = vol.Schema({
    vol.Required('number'): cv.positive_int,
})

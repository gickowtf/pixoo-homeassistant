# pv_schema.py
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

PV_SCHEMA = vol.Schema({
    vol.Required('power'): cv.string,
    vol.Required('storage'): cv.string,
    vol.Required('discharge'): cv.string,
    vol.Required('powerhousetotal'): cv.string,
    vol.Required('vomNetz'): cv.string,
    vol.Required('time'): cv.string,
})

# __init__.py
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import logging
from .const import CURRENT_ENTRY_VERSION, DOMAIN, VERSION
from .pixoo64 import Pixoo

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Divoom Pixoo from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    await async_detect_and_fix_old_entry(hass, entry)  # Tries to detect and fix old entries.
    _LOGGER.debug("Setting up entry %s.", entry.entry_id)

    try:
        pix = await hass.async_add_executor_job(load_pixoo, entry.options.get('ip_address'))
    except Exception as e:
        _LOGGER.error("Error setting up Pixoo: %s", e)
        return False

    hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id]['pixoo'] = pix
    hass.data[DOMAIN][entry.entry_id]['entry_data'] = entry.options

    await hass.config_entries.async_forward_entry_setups(entry, ["light", "sensor"])
    hass.data[DOMAIN][entry.entry_id]['update_listener'] = entry.add_update_listener(async_update_entry)

    return True


def load_pixoo(ip_address: str):
    """Load the Pixoo device. This is a blocking call."""
    return Pixoo(ip_address)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry. Called by HA."""
    _LOGGER.debug("Unload entry %s.", entry.entry_id)

    hass.data[DOMAIN][entry.entry_id]['update_listener']()  # Unlisten the update listener
    del hass.data[DOMAIN][entry.entry_id]

    return await hass.config_entries.async_unload_platforms(entry, ["light", "sensor"])


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Called by HA when the config entry is updated. Reloads don't count!
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
    _LOGGER.debug("Updated entry %s.", entry.entry_id)


async def async_detect_and_fix_old_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Detect old entry. Called for every entry when HA find the versions don't match."""
    if config_entry.options["pages_data"] and "page" in config_entry.options["pages_data"][0]:
        # Detected a v1 entry
        config_entry.version = 1
        await async_migrate_entry(hass, config_entry)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry. Called for every entry when HA find the versions don't match."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version > CURRENT_ENTRY_VERSION:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:
        old = {**config_entry.options}
        new = {}
        new["ip_address"] = old.get("ip_address")
        new["scan_interval"] = old.get("scan_interval")
        new["pages_data"] = []

        for old_page in old.get("pages_data"):
            if "PV" in old_page:
                new["pages_data"].append({"page_type": "PV", **old_page["PV"][0]})
            elif "texts" in old_page or "images" in old_page:
                new_page = {"page_type": "components", "components": []}

                for text in old_page.get("texts", []):
                    old_font = text.get("font", "FONT_PICO_8")
                    new_font = "PICO_8" if old_font == "FONT_PICO_8" else "GICKO" if old_font == "FONT_GICKO" else old_font

                    new_page["components"].append(
                        {"type": "text", "content": text.get("text", ""), "position": text.get("position", [0, 0]),
                         "font": new_font, "color": text.get("font_color", [255, 255, 255])})
                for image in old_page.get("images", []):
                    new_page["components"].append({"type": "image", "image_path": image.get("image", ""),
                                                   "position": image.get("position", [0, 0])})
                new["pages_data"].append(new_page)
            elif "channel" in old_page:
                new["pages_data"].append({"page_type": "channel", "id": old_page["channel"][0]["number"]})
            elif "clockId" in old_page:
                new["pages_data"].append({"page_type": "clock", "id": old_page["clockId"][0]["number"]})
            elif "Fuel" in old_page:
                new["pages_data"].append({"page_type": "fuel", **old_page["Fuel"][0]})
        hass.config_entries.async_update_entry(config_entry, options=new)
        config_entry.version = 2
        _LOGGER.debug("Migrated config to version 2. New config: %s", config_entry.options)

    if config_entry.version != CURRENT_ENTRY_VERSION:
        _LOGGER.error("Migration failed for entry %s.", config_entry.entry_id)
        return False

    _LOGGER.debug("Migration to version %s successful", config_entry.version)
    return True

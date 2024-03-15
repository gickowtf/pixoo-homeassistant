# _pages.py
from .solar import solar
from .fuel import fuel
from ..pixoo64._font import FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX

special_pages = {
    "pv": lambda pixoo, hass, page: solar(pixoo, hass, page, FONT_PICO_8, FONT_GICKO),
    "fuel": lambda pixoo, hass, page: fuel(pixoo, hass, page, FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX),
}
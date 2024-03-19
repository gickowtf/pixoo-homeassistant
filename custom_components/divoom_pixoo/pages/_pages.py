# _pages.py
from .solar import solar
from .fuel import fuel
from .progress_bar import progress_bar
from ..pixoo64._font import FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX, CLOCK

special_pages = {
    "pv": lambda pixoo, hass, page: solar(pixoo, hass, page, FONT_PICO_8, FONT_GICKO),
    "fuel": lambda pixoo, hass, page: fuel(pixoo, hass, page, FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX),
    "progress_bar": lambda pixoo, hass, page: progress_bar(pixoo, hass, page, FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX, CLOCK),
}
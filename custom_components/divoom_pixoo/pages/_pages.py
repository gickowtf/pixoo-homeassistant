# _pages.py
from .solar import solar
from .fuel import fuel
from .progress_bar import progress_bar
from ..pixoo64._font import FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX, CLOCK

special_pages = {
    "pv": lambda pixoo, hass, page, font_manager=None: solar(
        pixoo, hass, page,
        font_manager.get_font("PICO_8") if font_manager else FONT_PICO_8,
        font_manager.get_font("GICKO") if font_manager else FONT_GICKO,
    ),
    "fuel": lambda pixoo, hass, page, font_manager=None: fuel(
        pixoo, hass, page,
        font_manager.get_font("PICO_8") if font_manager else FONT_PICO_8,
        font_manager.get_font("GICKO") if font_manager else FONT_GICKO,
        font_manager.get_font("FIVE_PIX") if font_manager else FIVE_PIX,
        font_manager.get_font("ELEVEN_PIX") if font_manager else ELEVEN_PIX,
    ),
    "progress_bar": lambda pixoo, hass, page, font_manager=None: progress_bar(
        pixoo, hass, page,
        font_manager.get_font("PICO_8") if font_manager else FONT_PICO_8,
        font_manager.get_font("GICKO") if font_manager else FONT_GICKO,
        font_manager.get_font("FIVE_PIX") if font_manager else FIVE_PIX,
        font_manager.get_font("ELEVEN_PIX") if font_manager else ELEVEN_PIX,
        font_manager.get_font("CLOCK") if font_manager else CLOCK,
    ),
}
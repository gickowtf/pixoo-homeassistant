#progress_bar.py
from homeassistant.helpers.template import Template
from homeassistant.exceptions import TemplateError
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)

def progress_bar(pixoo, hass, page_data: dict, FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX, CLOCK):
    pixoo.clear()

    #Datetime
    now = datetime.now()
    time = now.strftime("%H:%M")

    red = "(255, 0, 68)"
    grey = (51, 51, 51)
    timeColor = "(51, 51, 51)"
    white = "(255, 255, 255)"
    blue = "(0, 123, 255)"

    for key in page_data.keys():  # Convert all values to strings. Avoids problems.
        page_data[key] = str(page_data[key])

    try:
        header = str(Template(page_data['header'], hass).async_render())
        progress = int(Template(page_data['progress'], hass).async_render())
        footer = str(Template(page_data['footer'], hass).async_render())

    except TemplateError as e:
        _LOGGER.error("Template render error: %s", e)
        return  # Stop execution if there is a template error


    bg_color = eval(page_data.get('bg_color', blue))
    header_offset = int(page_data.get('header_offset', 2))
    header_font_color = eval(page_data.get('header_font_color', white))
    progress_bar_color = eval(page_data.get('progress_bar_color', red))
    progress_text_color = eval(page_data.get('progress_text_color', white))
    time_color = eval(page_data.get('time_color', timeColor))
    footer_offset = int(page_data.get('footer_offset', 2))
    footer_font_color = eval(page_data.get('footer_font_color', white))

    #backgroundcolor
    pixoo.draw_filled_rectangle((0,0), (63,63), bg_color)

    #header
    pixoo.draw_filled_rectangle((0,0), (63,6), grey)
    pixoo.draw_text(header, (header_offset, 1), header_font_color , FIVE_PIX)

    #progress bar
    pixoo.draw_filled_rectangle((2, 25), (61, 33), grey)
    percent_size = int(60/100 * progress)
    pixoo.draw_filled_rectangle((3,26),(percent_size,32), progress_bar_color)
    pixoo.draw_text(f"{progress} %", (4,27), progress_text_color, FONT_PICO_8)

    #time
    pixoo.draw_text(time, (15,10), time_color, CLOCK)

    #footer
    pixoo.draw_filled_rectangle((0,57), (63, 63), grey)
    pixoo.draw_text(footer, (footer_offset,58), footer_font_color, FIVE_PIX)
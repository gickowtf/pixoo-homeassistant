from homeassistant.helpers.template import Template
from homeassistant.exceptions import TemplateError
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)

def fuel(pixoo, hass, page_data, FONT_PICO_8, FONT_GICKO, FIVE_PIX, ELEVEN_PIX):
    for fuel in page_data["Fuel"]:
        pixoo.clear()

        #Datetime
        now = datetime.now()
        day = now.strftime("%a")
        time = now.strftime("%H:%M")
        date = now.strftime("%d-%m")

        #colors
        darkgrey = (36, 36, 36)  #datetime bg
        black = (0, 0, 0) #default title
        white = (255, 255, 255)  #date
        yellow = (255, 230, 0) #default bg + time

        try:
            title = str(Template(fuel['title'], hass).async_render())
            name1 = str(Template(fuel['name1'], hass).async_render())
            price1 = str(Template(fuel['price1'], hass).async_render())
            name2 = str(Template(fuel['name2'], hass).async_render())
            price2 = str(Template(fuel['price2'], hass).async_render())
            name3 = str(Template(fuel['name3'], hass).async_render())
            price3 = str(Template(fuel['price3'], hass).async_render())
            status = str(Template(fuel['status'], hass).async_render())
        except TemplateError as e:
            _LOGGER.error("Template render error: %s", e)
            return  # Stop execution if there is a template error

        font_color = tuple(fuel.get('font_color', white))
        bg_color = tuple(fuel.get('bg_color', yellow))
        price_color = tuple(fuel.get('price_color', white))
        title_color = tuple(fuel.get('title_color', black))
        stripe_color = tuple(fuel.get('stripe_color', font_color))
        title_offset = fuel.get('title_offset', 2)

        pixoo.draw_filled_rectangle((0, 57), (64, 64), darkgrey)
        pixoo.draw_text(status, (1, 58), white, FIVE_PIX)

        #bg for names and prices
        pixoo.draw_filled_rectangle((0, 24), (64, 56), bg_color)

        #price names
        pixoo.draw_filled_rectangle((0, 26), (61, 33), darkgrey)
        pixoo.draw_text(f"{name1}", (1, 28), font_color, FIVE_PIX)
        pixoo.draw_filled_rectangle((0, 36), (61, 43), darkgrey)
        pixoo.draw_text(f"{name2}", (1, 38), font_color, FIVE_PIX)
        pixoo.draw_filled_rectangle((0, 46), (61, 53), darkgrey)
        pixoo.draw_text(f"{name3}", (1, 48), font_color, FIVE_PIX)

        # bg for names and prices
        # if names longer than prices starts they getting cut
        pixoo.draw_filled_rectangle((31, 24), (64, 56), bg_color) #if names longer than prices starts they getting cut
        pixoo.draw_filled_rectangle((0, 56), (64,56), stripe_color) #stripe

        #price1
        pixoo.draw_filled_rectangle((31, 26), (61, 33), darkgrey)
        pixoo.draw_text(f"{price1}", (33, 27), price_color, FONT_GICKO)

        #price2
        pixoo.draw_filled_rectangle((31, 36), (61, 43), darkgrey)
        pixoo.draw_text(f"{price2}", (33, 37), price_color, FONT_GICKO)

        #price3
        pixoo.draw_filled_rectangle((31, 46), (61, 53), darkgrey)
        pixoo.draw_text(f"{price3}", (33, 47), price_color, FONT_GICKO)

        #header
        pixoo.draw_filled_rectangle((0, 0), (63, 19), bg_color)
        pixoo.draw_text(title.upper(), (title_offset, 2), title_color, ELEVEN_PIX)
        pixoo.draw_filled_rectangle((0, 15), (64, 15), stripe_color) #stripe
        pixoo.draw_filled_rectangle((0, 16), (64, 22), darkgrey)
        pixoo.draw_filled_rectangle((0, 23), (64, 23), stripe_color) #stripe
        pixoo.draw_text(day, (1, 17), font_color, FIVE_PIX)
        pixoo.draw_text(time, (22, 17), bg_color, FONT_PICO_8)
        pixoo.draw_text(date, (45, 17), font_color, FONT_PICO_8)

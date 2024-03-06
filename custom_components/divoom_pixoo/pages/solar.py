from homeassistant.helpers.template import Template
from homeassistant.exceptions import TemplateError
import logging

_LOGGER = logging.getLogger(__name__)

def solar(pixoo, hass, page_data, FONT_PICO_8, FONT_GICKO):
    for solar in page_data["PV"]:
        pixoo.clear()
        try:
            rendered_power = float(Template(solar['power'], hass).async_render())
            rendered_storage = float(Template(solar['storage'], hass).async_render())
            rendered_discharge = float(Template(solar['discharge'], hass).async_render())
            rendered_powerhousetotal = float(Template(solar['powerhousetotal'], hass).async_render())
            rendered_vomNetz = float(Template(solar['vomNetz'], hass).async_render())
            rendered_time = str(Template(solar['time'], hass).async_render())
        except TemplateError as e:
            _LOGGER.error("Template render error: %s", e)
            return  # Stop execution if there is a template error

        image_folder = "/config/custom_components/divoom_pixoo/img/"

        battery_images = [
            (image_folder + "akku00-20.png", 0),
            (image_folder + "akku20-40.png", 20),
            (image_folder + "akku40-60.png", 40),
            (image_folder + "akku60-80.png", 60),
            (image_folder + "akku80-100.png", 80)
        ]

        green = (4, 204, 2) #discharge
        red = (255, 0, 68) #discharge
        grey = (131, 131, 131) #power vomNetz
        white = (255, 255, 255) #time
        yellow = (255, 175, 0) #power
        blue = (0, 123, 255) #powerhousetotal

        #Time
        pixoo.draw_text(rendered_time, (44, 1), white, FONT_PICO_8)

        #Power
        pixoo.draw_image(image_folder + "sunpower.png", (1, 0))

        if rendered_power >= 1:
            pixoo.draw_text(f'{rendered_power}', (17, 8), yellow, FONT_GICKO)
        else:
            pixoo.draw_text(f'{rendered_power}', (17, 8), grey, FONT_GICKO)

        if rendered_discharge <= 0:
            pixoo.draw_text(f'{rendered_discharge}', (17, 18), red, FONT_GICKO)
        else:
            pixoo.draw_text(f'{rendered_discharge}', (17, 18), green, FONT_GICKO)

        for image_path, threshold in battery_images:
            if rendered_storage >= threshold:
                pixoo.draw_image(image_path, (1, 16))
                break

        pixoo.draw_text(f"{rendered_storage}%", (17, 25), white, FONT_PICO_8)

        pixoo.draw_image(image_folder + "haus.png", (1, 32))
        pixoo.draw_text(f"{rendered_powerhousetotal}", (17, 40), blue, FONT_GICKO)

        pixoo.draw_image(image_folder + "industry.png", (1, 48))
        pixoo.draw_text(f'{rendered_vomNetz}', (17, 56), grey, FONT_GICKO)

from homeassistant.helpers.template import Template
from homeassistant.exceptions import TemplateError

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

        green = (4, 204, 2) #discharge
        red = (255, 0, 68) #discharge
        grey = (131, 131, 131) #power vomNetz
        white = (255, 255, 255) #time
        yellow = (255, 175, 0) #power
        blue = (0, 123, 255) #powerhousetotal

        #Time
        pixoo.draw_text(rendered_time, (44, 1), white, FONT_PICO_8)

        #Power
        pixoo.draw_image("/config/custom_components/divoom_pixoo/img/sunpower.png", (1, 0))

        if rendered_power >= 1:
            pixoo.draw_text(f'{rendered_power}', (17, 8), yellow, FONT_GICKO)
        else:
            pixoo.draw_text(f'{rendered_power}', (17, 8), grey, FONT_GICKO)

        if rendered_discharge <= 0:
            pixoo.draw_text(f'{rendered_discharge}', (17, 18), red, FONT_GICKO)
        else:
            pixoo.draw_text(f'{rendered_discharge}', (17, 18), green, FONT_GICKO)

        if rendered_storage >= 0:
            pixoo.draw_image("/config/custom_components/divoom_pixoo/img/akku00-20.png", (1, 16))
        if rendered_storage >= 20:
            pixoo.draw_image("/config/custom_components/divoom_pixoo/img/akku20-40.png", (1, 16))
        if rendered_storage >= 40:
            pixoo.draw_image("/config/custom_components/divoom_pixoo/img/akku40-60.png", (1, 16))
        if rendered_storage >= 60:
            pixoo.draw_image("/config/custom_components/divoom_pixoo/img/akku60-80.png", (1, 16))
        if rendered_storage >= 80:
            pixoo.draw_image("/config/custom_components/divoom_pixoo/img/akku80-100.png", (1, 16))

        pixoo.draw_text(f"{rendered_storage}%", (17, 25), white, FONT_PICO_8) #FONT_PICO_8

        pixoo.draw_image("/config/custom_components/divoom_pixoo/img/haus.png", (1, 32))
        pixoo.draw_text(f"{rendered_powerhousetotal}", (17, 40), blue, FONT_GICKO)

        pixoo.draw_image("/config/custom_components/divoom_pixoo/img/industry.png", (1, 48))
        pixoo.draw_text(f'{rendered_vomNetz}', (17, 56), grey, FONT_GICKO)

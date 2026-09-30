How to get [weather (current or forcast)](https://www.home-assistant.io/integrations/weather/) onto a page.

The following samples use `weather.forecast_home` as the data source, which might be different in your installation.

## Current

The current weather can be accessed directly via:
* status: `states('weather.forecast_home')` (like sunny, cloudy, ...)
* attributes: `state_attr('weather.forecast_home', 'temperature')` (here the temperature, use "Developer tools" -> "States" to see the available).

## Forecast

Forecast is a bit more complicated as you have to use the `weather.get_forecasts` service.

[Templates](https://www.home-assistant.io/integrations/template#yaml-configuration) are one option to do that. 
The following sample extracts values from +3h, +6h, +1d and +2d every 10 minutes and saves them as `sensor.weather_forecast_plus...`.
```yaml
template:
  - trigger:
      - trigger: time_pattern
        minutes: /10
    action:
      - action: weather.get_forecasts
        data:
          type: hourly
        target:
          entity_id: weather.forecast_home
        response_variable: hourly
      - action: weather.get_forecasts
        data:
          type: daily
        target:
          entity_id: weather.forecast_home
        response_variable: daily
    sensor:
      - name: Weather Forecast in 3 hours
        unique_id: weather_forecast_plus_3_hours
        state: "{{ hourly['weather.forecast_home'].forecast[3].condition }}"
      - name: Weather Temperature in 3 hours
        unique_id: weather_temperature_plus_3_hours
        state: "{{ hourly['weather.forecast_home'].forecast[3].temperature }}"
      - name: Weather Forecast in 6 hours
        unique_id: weather_forecast_plus_6_hours
        state: "{{ hourly['weather.forecast_home'].forecast[6].condition }}"
      - name: Weather Temperature in 6 hours
        unique_id: weather_temperature_plus_6_hours
        state: "{{ hourly['weather.forecast_home'].forecast[6].temperature }}"
      - name: Weather Forecast in 1 day
        unique_id: weather_forecast_plus_1_days
        state: "{{ daily['weather.forecast_home'].forecast[1].condition }}"
      - name: Weather Temperature in 1 day
        unique_id: weather_temperature_plus_1_days
        state: "{{ daily['weather.forecast_home'].forecast[1].temperature }}"
      - name: Weather Forecast in 2 days
        unique_id: weather_forecast_plus_2_days
        state: "{{ daily['weather.forecast_home'].forecast[2].condition }}"
      - name: Weather Temperature in 2 days
        unique_id: weather_temperature_plus_2_days
        state: "{{ daily['weather.forecast_home'].forecast[2].temperature }}"
```

Use the following for the hourly sensors to also include the sun setting for adjusting `sunny` <-> `clear-night` and `partlycloudy` <-> `partlycloudy-night`.
```yaml
      - name: Weather Forecast in 3 hours
        unique_id: weather_forecast_plus_3_hours
        state: "
        {% set cond = hourly['weather.forecast_home'].forecast[3].condition %}
        {% set next_setting = as_timestamp(state_attr('sun.sun', 'next_setting')) %}
        {% set next_rising = as_timestamp(state_attr('sun.sun', 'next_rising')) %}
        {% set time = as_timestamp(hourly['weather.forecast_home'].forecast[3].datetime) %}
        
        {% if ((time > next_setting and time < next_rising) or (time < next_setting and time < next_rising and next_rising < next_setting)) %}
          {% if cond == 'sunny' %} clear-night {% elif cond == 'partlycloudy' %} partlycloudy-night {% else %} {{ cond }} {% endif %}
        {% else %}
          {% if cond == 'clear-night' %} sunny {% else %} {{ cond }} {% endif %}
        {% endif %}
        "
```

## Page

This sample shows how to use this data on a page.

```yaml
- page_type: components
  components:
    # current temperature (or other attributes)
    - type: text
      content: "{{ state_attr('weather.forecast_home', 'temperature') }}"
    # current weather
    - type: image
      image_path: "{{ '/config/custom_components/divoom_pixoo/img/weather/' + states('weather.forecast_home') + '.png' }}"
    # temperature forecast from as template defined above
    - type: text
      content: "{{ states('sensor.weather_temperature_in_3_hours') }}"
    # weather forecast from as template defined above
    - type: image
      image_path: "{{ '/config/custom_components/divoom_pixoo/img/weather/' + states('sensor.weather_forecast_in_3_hours') + '.png' }}"
```

Use something like this when you also want to adjust the current weather with the sun setting.

```yaml
- page_type: components
  variables:
    current_weather: "{{ states('weather.forecast_home') }}"
    sun: "{{ states('sun.sun') }}"
  components:
    - type: image
      image_path: >-
        {{ '/config/custom_components/divoom_pixoo/img/weather/' +
        ('clear-night' if (sun == 'below_horizon' and current_weather == 'sunny') else
        'partlycloudy-night' if (sun == 'below_horizon' and current_weather == 'partlycloudy') else
        'sunny' if (sun == 'above_horizon' and current_weather == 'clear-night') else
        current_weather ) + '.png' }}
```

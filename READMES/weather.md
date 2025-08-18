How to get [weather (current or forcast)](https://www.home-assistant.io/integrations/weather/) onto a page.

The following samples use `weather.forecast_home` as the data source, which might be different in your installation.

## Current

The current weather can be accessed directly via:
* status: `states('weather.forecast_home')` (like sunny, cloudy, ...)
* attributes: `state_attr('weather.forecast_home', 'temperature')` (here the temperature, use "Developer tools" -> "States" to see the available).

## Forecast

Forecast is a bit more complicated as you have to use the `weather.get_forecasts` service.

[Templates](https://www.home-assistant.io/integrations/template#yaml-configuration) are one option to do that. 
The following sample extracts values from +3h, +6h, +1d and +2d every 10 minutes and saves them as `sensor.weather_forecast_plus...`:
```
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
        state: "{{ hourly['weather.forecast_home'].forecast[2].condition }}"
      - name: Weather Temperature in 3 hours
        unique_id: weather_temperature_plus_3_hours
        state: "{{ hourly['weather.forecast_home'].forecast[2].temperature }}"
      - name: Weather Forecast in 6 hours
        unique_id: weather_forecast_plus_6_hours
        state: "{{ hourly['weather.forecast_home'].forecast[5].condition }}"
      - name: Weather Temperature in 6 hours
        unique_id: weather_temperature_plus_6_hours
        state: "{{ hourly['weather.forecast_home'].forecast[5].temperature }}"
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

## Page

This sample shows how to use this data on a page:

```
- page_type: components
  variables:
    d_1: "{{ now().strftime('%a') }}"
    d_2: "{{ (now() + timedelta(days=1)).strftime('%a') }}"
    d_3: "{{ (now() + timedelta(days=2)).strftime('%a') }}"
    w_1_t: "{{ state_attr('weather.forecast_home', 'temperature') }}"
    w_1_s: "{{ states('weather.forecast_home') }}"
    w_2_t: "{{ states('sensor.weather_temperature_in_3_hours') }}"
    w_2_s: "{{ states('sensor.weather_forecast_in_3_hours') }}"
    w_3_t: "{{ states('sensor.weather_temperature_in_6_hours') }}"
    w_3_s: "{{ states('sensor.weather_forecast_in_6_hours') }}"
    w_4_t: "{{ states('sensor.weather_temperature_in_1_day') }}"
    w_4_s: "{{ states('sensor.weather_forecast_in_1_day') }}"
    w_5_t: "{{ states('sensor.weather_temperature_in_2_days') }}"
    w_5_s: "{{ states('sensor.weather_forecast_in_2_days') }}"
  components:
    - type: text
      content: "{{ d_1 }}"
      position:
        - 19
        - 28
      font: pico_8
      color: grey
      align: center
    - type: text
      position:
        - 7
        - 45
      content: "{{ '{:.0f}'.format(w_1_t) }}"
      font: pico_8
      color: white
      align: center
    - type: image
      position:
        - 3
        - 35
      image_path: "{{ '/config/custom_components/divoom_pixoo/img/weather/' + w_1_s + '.png' }}"
    - type: text
      position:
        - 19
        - 45
      content: "{{ '{:.0f}'.format(w_2_t) }}"
      font: pico_8
      color: white
      align: center
    - type: image
      position:
        - 15
        - 35
      image_path: "{{ '/config/custom_components/divoom_pixoo/img/weather/' + w_2_s + '.png' }}"
      height: 8
      width: 8
    - type: text
      position:
        - 30
        - 45
      content: "{{ '{:.0f}'.format(w_3_t) }}"
      font: pico_8
      color: white
      align: center
    - type: image
      position:
        - 27
        - 35
      image_path: "{{ '/config/custom_components/divoom_pixoo/img/weather/' + w_3_s + '.png' }}"
    - type: text
      content: "{{ d_2 }}"
      position:
        - 43
        - 28
      font: pico_5
      color: grey
      align: center
    - type: text
      position:
        - 43
        - 45
      content: "{{ '{:.0f}'.format(w_4_t) }}"
      font: pico_8
      color: white
      align: center
    - type: image
      position:
        - 39
        - 35
      image_path: "{{ '/config/custom_components/divoom_pixoo/img/weather/' + w_4_s + '.png' }}"
    - type: text
      content: "{{ d_3 }}"
      position:
        - 57
        - 28
      font: pico_5
      color: grey
      align: center
    - type: text
      position:
        - 57
        - 45
      content: "{{ '{:.0f}'.format(w_5_t) }}"
      font: pico_8
      color: white
      align: center
    - type: image
      position:
        - 53
        - 35
      image_path: "{{ '/config/custom_components/divoom_pixoo/img/weather/' + w_5_s + '.png' }}"
```

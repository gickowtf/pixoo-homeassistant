<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/logo.png?raw=true" title="Example of configuration.yaml" align="right" height="90" />

# Divoom Pixoo 64 Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/gickowtf)
![python badge](https://img.shields.io/badge/Made%20with-Python-orange)
![last commit](https://img.shields.io/github/last-commit/gickowtf/pixoo-homeassistant?color=red)


Custom component for easy use of a Pixoo64 within Home Assistant.
With this integration you have the possibility to display different designs and personalize them with information from the Home Assistant.
For example, you can use this integration to display several texts {{ templates }} and images on one page.
You can also use this integration to determine how long you want to see a page, e.g. you can set the page to change every 15 seconds.
In addition, you also have a light entity for switching the display on and off or changing the brightness. 
Last but not least, you can create automations with which you can use certain triggers to display the pages that are available to you as a push.

## Installation
1. Install this integration with HACS (adding repository required), or copy the contents of this
repository into the `custom_components/divoom_pixoo` directory.
2. Restart Home Assistant.
3. Go to Settings / Integrations and add integration "Divoom Pixoo 64"
4. Please select a discovered Pixoo 64 device from the list or select 'Manual IP' to manually enter the device's IP.


### configuration 
**IP address of the device:** discovered or manually entered IP

**Scan interval (in seconds):** #default 15 seconds (this is the time a page is displayed )

**List of pages in JSON * :** 

<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/pixoo.gif?raw=true" title="Example of configuration.yaml Solar" align="left" height="150" width="150" />

```yaml
- page_type: PV
  enabled: "{{ states.input_boolean.YOURS.state }}"  #is only displayed if the state = 'true', 'yes', 'on' or '1'
  power: "{{ states.sensor.YOUR_SENSOR.state }}"
  storage: "{{ states.sensor.YOUR_SENSOR.state }}"
  discharge: "{{ states.sensor.YOUR_SENSOR.state }}"
  powerhousetotal: "{{ states.sensor.YOUR_SENSOR.state }}"
  vomNetz: "{{ states.sensor.YOUR_SENSOR.state }}"
  time: "{{ now().strftime('%H:%M') }}"
- page_type: components
  enabled: "{{ states.input_boolean.YOURS.state }}"  #is only displayed if the state = 'true', 'yes', 'on' or '1'
  components:
  - type: text
    position: [0, 10]
    content: "2 github/gickowtf"
    font: PICO_8
    color: [255, 0, 0] # or write "red"
  - type: image
    image_path: "/config/img/haus.png" #max 64 x 64 Pixel
    position: [10, 30]
- page_type: clock #in this case 'enabled' is omitted and is set to true by default
  id: 182
```
<br>

--------------


## - page_type

| **Keywords** | **Values**                           |
|:-------------|:-------------------------------------| 
| - page_type: | required the name of the page_type   |

for example:
```yaml
- page_type: components
```
<br>

--------------

### enabled:

| **Keywords** | **Values**                                                                                          |
|:-------------|:----------------------------------------------------------------------------------------------------| 
| enabled:     | optional (default true) {{ template }} #is only displayed if the state = 'true', 'yes', 'on' or '1' |

```yaml
- page_type: PAGE_TYPE
  enabled: "{{ states.input_boolean.YOURS.state }}"
```

<br>

--------------

### components
*- page_type: components*

| **Keywords**            | **Values**                                 |
|:------------------------|:-------------------------------------------|
| - page_type: components | to use this page_type                      |
| components:             | - type: text or - type: image **required** |


| **Keywords** | **Values**                                                                      |
|:-------------|:--------------------------------------------------------------------------------|
| - type: text |                                                                                 |
| position     | **required** The text [position](#positioning) on a XY axis at 64x64 pixel      |
| content      | **required** {{ templates }} and [Newline](#newline) Support in text            |
| font         | default PICO_8  [Fonts](#fonts)                                                 |
| color        | default white [R, G, B] or [Colors](#colors)                                    |

| **Keywords**   | **Values**                                                                                                                                   |
|:---------------|:---------------------------------------------------------------------------------------------------------------------------------------------|
| - type: image  |                                                                                                                                              |
|                | **one of following image_xxx is required**                                                                                                   |
| image_path     | image path like /config/img/haus.png                                                                                                         |
| image_url      | image url like template {{ entity image }} or https://raw.githubusercontent.com/gickowtf/pixoo-homeassistant/main/images/pixoo.gif           |
| image_data     | image data in base64  convert images [here](https://base64.guru/converter/encode/image)                                                      |
|                |                                                                                                                                              |
| position       | **required** The image [position](#positioning) on a XY axis at 64x64 pixel                                                                  |
|                |                                                                                                                                              |
| height         | **optional** If none is selected, the image will be at it's original size. If one is selected, it will become the longest side. Proportional |
| width          | **optional** If none is selected, the image will be at it's original size. If one is selected, it will become the longest side. Proportional |
| resample_mode  | **optional** default = `box` <br> `nearest`,  `bilinear`,  `hamming`, `bicubic`, `lanczos`                                                   |

```yaml
- page_type: components
  enabled: "{{ states.input_boolean.YOURS.state }}" #optional
  components:
    - type: text
      position: [10, 0]
      content: 2 github/gickowtf #
      font: PICO_8
      color: [255, 0, 0]
    - type: image
      image_path: /config/img/haus.png
      position: [30, 30]
    - type: image
      position: [0, 0]
      image_url: >-
        https://raw.githubusercontent.com/gickowtf/pixoo-homeassistant/main/images/pixoo.gif
      resample_mode: box #optional
      height: 30 #optional
    - type: image
      position: [30, 0]
      image_data: >-
        iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPBAMAAADJ+Ih5AAAAGFBMVEX//8z//5n//2b//zP//wDMzAAAAADAwMB5Mg5mAAAACHRSTlP/////////AN6DvVkAAAABYktHRAcWYYjrAAAAaklEQVR42kXNsQ2AIBBA0Wsc4ExcAKMLGAcwogModzUaOVoqWF8wJHav+h9SEhGfAqQIqMYCm9H7ABEIqd8D2EYWMZv9cSGiWgs6bNWZcfOhBlcxfyBHbMhCnFjcxrn8aK3Jl5cm4vKq9xdiSyWVldcCmgAAAHB0RVh0Y29tbWVudABpY29uNy5naWYgZm9yIHVzZSBpbiBVQkINCg0KKEMpIDE5OTkgUGhpbGlwcCBFc3NlbGJhY2ggKHBsZUBnbXgubmV0KQ0KaHR0cDovL3d3dy5udGdhbWVwYWxhY2UuaXNjb29sLm5ldBIZgm0AAAAASUVORK5CYII=
      resample_mode: nearest #optional
      height: 8 #optional
```
<br>

### Positioning

<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/XY.png?raw=true" title="Example XY axis"  height="300" />


### Newline

**Newline Support** in `content:` example:
```yaml
  content: |-
    text 1
    {{ states.*.state }}
```
*There is no limit to the maximum newlines except for 64 pixels ;)*

<br>

--------------



### PV 
Photovoltaic - PV is a pre-designed page. The icon changes depending on the battery capacity and the font color changes from red to green

*Helper entities may have to be used here*

| **Keywords**    | **Values**                             |                                                                                                                                                                         |
|:----------------|:---------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| - page_type: PV | to use this page_type                  | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/solar.png?raw=true" title="Example of configuration.yaml Solar" align="left" height="150" /> |
| power           | **required**  use {{ template }}       | Current power from the photovoltaic system                                                                                                                              |
| storage         | **required**      use {{ template }}   | Battery storage in percent                                                                                                                                              |
| discharge       | **required**      use {{ template }}   | Current charging/discharging power                                                                                                                                      |
| powerhousetotal | **required**      use {{ template }}   | Current power consumption of the house                                                                                                                                  |
| vomNetz         | **required**      use {{ template }}   | Current consumption from grid or feed-in                                                                                                                                |
| time            | **required**        use {{ template }} | Current time example: {{ now().strftime("%H:%M") }}                                                                                                                     |

```yaml
- page_type: PV
  enabled: "{{ states.input_boolean.test2.state }}"
  power: "{{ states.sensor.enpal_solar_production_power.state }}"
  storage: "{{ states.sensor.enpal_battery_percent.state }}"
  discharge: "{{ states.sensor.enpal_battery_power.state }}"
  powerhousetotal: "{{ states.sensor.enpal_power_house_total.state }}"
  vomNetz: "{{ states.sensor.enpal_power_external_total.state }}"
  time: "{{ now().strftime('%H:%M') }}"
```
<br>

--------------



### Fuel 
*Special Page for Gas Station Pricing. Helper entities may have to be used here*

<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/gasstation.jpg?raw=true" title="Example of configuration.yaml Solar" align="left" />
<br>



| **Keywords**          | **Values**                                         |                                                                                                                                                                        |
|:----------------------|:---------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| - page_type: Fuel     | to use this page_type                              | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/fuel.png?raw=true" title="Example of configuration.yaml Solar" align="left" height="150" /> |
| title                 | -required use {{ template }}                       | Title e.g. Gas Station Name                                                                                                                                            |
| name1                 | -required     use {{ template }}                   | e.g. fuel type                                                                                                                                                         |
| price1                | -required     use {{ template }}                   | fuel price                                                                                                                                                             |
| name2                 | -required     use {{ template }}                   | e.g. fuel type                                                                                                                                                         |
| price2                | -required     use {{ template }}                   | fuel price                                                                                                                                                             |
| name3                 | -required     use {{ template }}                   | e.g. fuel type                                                                                                                                                         |
| price3                | -required     use {{ template }}                   | fuel price                                                                                                                                                             |
| status                | -required     use {{ template }}                   | Any extra field in my case an opening status                                                                                                                           |
|                       |                                                    |                                                                                                                                                                        |
| font_color            | -optional     use "[R, G, B]" or [Colors](#colors) | RGB Color #default white                                                                                                                                               |
| bg_color              | -optional     use "[R, G, B]" or [Colors](#colors) | RGB Color #default yellow (255, 230, 0)                                                                                                                                |
| price_color           | -optional     use "[R, G, B]" or [Colors](#colors) | RGB Color #default white                                                                                                                                               |
| title_color           | -optional     use "[R, G, B]" or [Colors](#colors) | RGB Color #default black                                                                                                                                               |
| stripe_color          | -optional     use "[R, G, B]" or [Colors](#colors) | RGB Color #default font_color                                                                                                                                          |
| title_offset          | -optional     use integers                         | to center the text #default 2                                                                                                                                          |

Example of the image:
```yaml
- page_type: Fuel
  enabled: "{{ states.input_boolean.YOURS.state }}"
  title: Classic
  name1: Diesel
  price1: "{{ states.sensor.diesel.state }}"
  name2: Super
  price2: "{{ states.sensor.super.state }}"
  name3: E10
  price3: "{{ states.sensor.e10.state }}"
  status: >-
    {% if is_state('binary_sensor.status', 'on') %} Offen {%
    else %} Geschlossen {% endif %}
  title_offset: "10"
  font_color: "[255, 255, 255]"
```

<br>

--------------
### Progress Bar
*Special page with a progress bar for, for example, the status of the dishwasher or charging status of the car*

| **Keywords**        | **Values**                                          |                                                                                                                                                                                     |
|:--------------------|:----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| - page_type: P      | to use this page_type                               | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/progressbar.png?raw=true" title="Example of configuration.yaml ProgressBar" align="left" height="150" /> |
| header              | -required use {{ template }}                        | e.g. Dishwasher                                                                                                                                                                     |
| progress            | -required     use {{ template }}                    | integer required                                                                                                                                                                    |
| footer              | -required     use {{ template }}                    | any footer e.g. Date                                                                                                                                                                | 
|                     |                                                     |                                                                                                                                                                                     |
| bg_color            | -optional     use "[R, G, B]" or [Colors](#colors)  | RGB Color #default blue                                                                                                                                                             |
| header_offset       | -optional     use int                               | integer required      #default 2                                                                                                                                                    |
| header_font_color   | -optional     use "[R, G, B]" or [Colors](#colors)  | RGB Color #default white                                                                                                                                                            |
| progress_bar_color  | -optional     use "[R, G, B]" or [Colors](#colors)  | RGB Color #default red                                                                                                                                                              |
| progress_text_color | -optional     use "[R, G, B]" or [Colors](#colors)  | RGB Color #default white                                                                                                                                                            |
| time_color          | -optional     use "[R, G, B]" or [Colors](#colors)  | RGB Color #default grey                                                                                                                                                             |
| footer_offset       | -optional     use int                               | integer required      #default 2                                                                                                                                                    |
| footer_font_color   | -optional     use "[R, G, B]" or [Colors](#colors)  | RGB Color #default white                                                                                                                                                            |


Example of the image:
```yaml
- page_type: progress_bar
  enabled: >-
    {% if is_state('sensor.DISHWASCHER_STATE', 'Run') %} true {%
    else %} false {% endif %}
  header: DISHWASHER
  progress: "{{ states.sensor.DISHWASHER_PROGRESS.state }}"
  footer: ANY FOOTER
  header_font_color: "[255, 255, 255]"
```

<br>

--------------

### channel 
*In Divoom app you can set three different custom channels which you can select here.*

| **Keywords**         | **Values**                                   |
|:---------------------|:---------------------------------------------|
| - page_type: channel | to use this page_type                        |
| id                   | 0 = channel 1, 1 = channel 2, 2 = channel 3  |

```yaml
- page_type: channel
  id: 0 #shows custom channel 1
```

<br>

--------------

### clock
*Channel - In Divoom app you can set three different custom channels which you can select here.*

| **Keywords**       | **Values**             |
|:-------------------|:-----------------------|
| - page_type: clock | to use this page_type  |
| id                 | int                    |

```yaml
- page_type: clock
  id: 182
```

[Here is a list of all ClockFaces](https://github.com/gickowtf/pixoo-homeassistant/blob/main/READMES/CLOCKS.md)

*or*

*To find out the number of the ClockFace, you can proceed as follows.*
1. First go to the settings and activate debug logging in the Divoom Pixoo 64 integration.
2. Now open the Divoom app on your smartphone and select your preferred ClockFace.
3. As soon as this is displayed on your Pixoo64, you will find "Device Data" in the log and then "CurClockId".
4. The CurClockId is the number you were looking for.

<br>

--------------
### visualizer

This adds the visualizer page to the integration. The id starts at zero and it represents the clocks from top left to bottom right as can be seen in the app.

<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/visualizer.png?raw=true" title="Example of visualizer"/>

```yaml
- page_type: visualizer
  id: 2
```
<br>

--------------

# Services


## Service Send a page to Divoom Pixoo (show_message) Push Notification

You can use it for Push Notifications. Trigger with anything! Call it with the Service "Divoom Pixoo 64: Send a page to Divoom Pixoo".

You can input in the _Page Data_ field the data of **one** page in the normal JSON format. It can be anything! (Please note that the 'enabled' tag doesn't work and that it's normal.)

Some examples of **Page Data:**
```yaml
page_type: clock
id: 182
```
or
```yaml
page_type: components
components:
  - type: text
    position: [10, 0]
    content: 2 github/gickowtf
    font: PICO_8
    color: [255, 0, 0]
  - type: image
    image_path: /config/img/haus.png
    position: [30, 30]
```

<br>

--------------
## Service Play a Buzzer 

Play the buzzer on the Divoom Pixoo. Beware that this maybe could damage the device. Use at your own risk.

**Buzzing Time per cycle.** in milliseconds `default: 500 milliseconds`<br>
The working time of the buzzer per cycle. The buzzer will not buzz continuously; it will go on and off in cycles (duration in-between not controllable).
 
**Idle Time per cycle** in milliseconds `default: 500 milliseconds`<br>
Idle time of the buzzer per cycle.

**Total Time** in milliseconds `default: 3000 milliseconds`<br>
The total time the buzzer will be working.

<br>

--------------

## Service Restart the Divoom Pixoo

Restart the Divoom Pixoo device. (It has a little bit of delay. Be patient.)


<br>

--------------

## Fonts
| **FONT** | **IMAGE**                                                                                                                              |
|:---------|:---------------------------------------------------------------------------------------------------------------------------------------|
| GICKO    | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/FONT_GICKO.png?raw=true" title="FONT_GICKO"  width="500" /> |
| FIVE_PIX | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/five_pix.png?raw=true" title="five_pix" width="500" />      |
| PICO_8   | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/PICO_8.png?raw=true" title="PICO_8" width="500" />          |

<br>

--------------

## Colors
<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/colors.png?raw=true" title="colors" />
<br>

--------------

## Issues

Sometimes the display crashes, especially with animated images. I have often read on the Internet that this is due to the power supply being too weak or the brightness being too high. I now have the display permanently set to **90%** and it no longer crashes.

<br>

--------------


## Discussions

I would be happy if you present your configuration.yaml in the Discussions area  
https://github.com/gickowtf/pixoo-homeassistant/discussions

<br>

--------------

## Disclaimer
This is not official software from Divoom.
It is a custom integration created by me (gickowtf) and therefore Divoom is not responsible for any damages/problems caused by this integration, nor does Divoom provide any end-user support for the integration.
Use this integration at your own risk.

<br>

--------------


## ❤️ Many thanks to
@Mrredstone5230 - Thanks for the conversion to config flow and many many more
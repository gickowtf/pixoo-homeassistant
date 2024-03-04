<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/logo.png?raw=true" title="Example of configuration.yaml" align="right" height="90" />

# Divoom Pixoo 64 Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/gickowtf)
![python badge](https://img.shields.io/badge/Made%20with-Python-orange)
![last commit](https://img.shields.io/github/last-commit/gickowtf/pixoo-homeassistant?color=red)

Custom component for easy use of a Pixoo64 within Home Assistant. With this integration you have the possibility to display different designs and personalize them with information from the Home Assistant. For example, you can use this integration to display several texts {{ templates }} and images on one page. You can also use this integration to determine how long you want to see a page, e.g. you can set the page to change every 15 seconds. In addition, you also have a light entity with which you can switch the display on and off time-controlled. Last but not least, you can create automations with which you can display text and images as a push using certain triggers.

## Installation
1. Install this integration with HACS (adding repository required), or copy the contents of this
repository into the `custom_components/pixoo-homeassistant` directory.
2. Restart Home Assistant.
3. Go to Settings / Integrations and add integration "Divoom Pixoo 64"
4. In the following window you can now enter the IP of your device and the update interval.
In the large text field below, enter the configuration


### configuration List of pages in JSON *:
 Just a small example with the HA logo and the current time!

<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/solar.jpg?raw=true" title="Example of configuration.yaml Solar" align="left" height="150" />

```
- page: 1
  PV:
    - power: "{{ states.sensor.YOUR_SENSOR.state }}"
      storage: "{{ states.sensor.YOUR_SENSOR.state }}"
      discharge: "{{ states.sensor.YOUR_SENSOR.state }}"
      powerhousetotal: "{{ states.sensor.YOUR_SENSOR.state }}"
      vomNetz: "{{ states.sensor.YOUR_SENSOR.state }}"
      time: "{{ now().strftime('%H:%M') }}"  #Format HH:MM
- page: 2
  texts:
    - text: "github/gickowtf"
      position: [0, 10]
      font: FONT_PICO_8
      font_color: [255, 0, 0]  # red
    - text: "Thx 4 Support"
      position: [0, 30]
      font: FONT_PICO_8
      font_color: [255, 0, 0]  # red
  images:
    - image: "/config/img/anyPicture.png" #max 64 x 64 Pixel
      position: [30, 10]
- page: 3
  channel:
    - number: 2
- page: 4
  clockId:
    - number: 39
```

## all options for configuration

### Basic settings required

| **Keywords**  | **Values**                                                                   |
|:--------------|:-----------------------------------------------------------------------------| 
| page          | required numbered by integers                                                |

<br>

--------------

<br>


### Page setting, here you can be creative and insert as much text and images as you like.

| **Keywords**   | **Values**                                                            |
|:---------------|:----------------------------------------------------------------------|
| texts          | required                                                              |
| text           | using templates or string - \n newline support                        |
| position       | The text position on a XY axis at 64x64 pixel                         |
| font           | at this time there are two different Fonts FONT_GICKO and FONT_PICO_8 |
| font_color     | RGB colors                                                            |
| images         | not required                                                          |
| image          | Path to the image including file name .png preferred                  |
| position       | The text position on a XY axis at 64x64 pixel                         |

<br>

### Position on XY axis

<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/XY.png?raw=true" title="Example XY axis"  height="300" />


### Newline Support

**Newline Support** in text with ```{{\n}}```
**There is no limit to the maximum newlines except for 64 pixels ;)**

**Example:** `text: Gicko{{\n}}Github`
or another Example: `text: {{ states.*.state }}{{\n}}{{ states.*.state }}

<br>

--------------

<br>



### Photovoltaic setting a self-designed design. The icon changes depending on the battery capacity and the font color changes from red to green
#### Helper entities may have to be used here
| **Keywords**    | **Values**                         |                                                                                                                                                                         |
|:----------------|:-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| PV              | own designed PV stats              | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/solar.jpg?raw=true" title="Example of configuration.yaml Solar" align="left" height="150" /> |
| power           | -required use {{ template }}       | Current power from the photovoltaic system                                                                                                                              |
| storage         | -required     use {{ template }}   | Battery storage in percent                                                                                                                                              |
| discharge       | -required     use {{ template }}   | Current charging/discharging power                                                                                                                                      |
| powerhousetotal | -required     use {{ template }}   | Current power consumption of the house                                                                                                                                  |
| vomNetz         | -required     use {{ template }}   | Current consumption from grid or feed-in                                                                                                                                |
| time            | -required     use {{ template }}   | Current time example: {{ now().strftime("%H:%M") }}                                                                                                                     |


<br>

--------------

<br>


### Custom Channel - In Divoom app you can set three different custom channels which you can select here. 
| **Keywords**    | **Values**                                   |
|:----------------|:---------------------------------------------|
| channel         | Custom Channel in APP                        |
| number          | 0 = channel 1, 1 = channel 2, 2 = channel 3  |

<br>

--------------

<br>

### ClockId Channel - In Divoom app you can set three different custom channels which you can select here. 
| **Keywords** | **Values**         |
|:-------------|:-------------------|
| clockId      | Clock Faces in APP |
| number       | int                |

If you have any further questions, I will be happy to help.

<br>

--------------

<br>

## Automation Example

You can use it for Push Notifications.
Trigger with anything!

Action with the Service "Divoom Pixoo 64: Use for push notifications".

#### IMPORTANT
**Display a message on the Divoom Pixoo. Please select the "... Current Page" entity of the device.**

In the following dialog you can define your push notification as usual in JSON format.

**Messages** 
The messages to display. Example: ["Hello World!", "How are you?"]

**Positions**
The positions of the components. Example: [[1,1], [1,20]]

**Colors**
List of RGB values for the texts. Example: [[255,0,0], [0,255,0]]

**Fonts**
List of the font for each text. Example: ["FONT_GICKO", "FONT_PICO_8"]

**Images**
The path to the images to display. Example: [ "/config/custom_components/divoom_pixoo/img/sunpower.png", "/config/custom_components/divoom_pixoo/img/haus.png" ]

**Image positions**
The positions of the images. Example: [[1,30], [20,30]]

<br>

--------------

<br>

## Font
| **FONT**     | **IMAGE**                                                                                                                 |
|:-------------|:--------------------------------------------------------------------------------------------------------------------------|
| FONT_GICKO   | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/FONT_GICKO.png?raw=true" title="FONT_GICKO" /> |
| FIVE_PIX     | *Image available soon*                                                                                                    |
| FONT_PICO_8  | *Image available soon*                                                                                                    |

<br>

--------------

<br>

## Issues

Sometimes the display crashes, especially with animated images. I have often read on the Internet that this is due to the power supply being too weak or the brightness being too high. I now have the display permanently set to **90%** and it no longer crashes.

<br>

--------------

<br>

## Discussions

I would be happy if you present your configuration.yaml in the Discussions area  
https://github.com/gickowtf/pixoo-homeassistant/discussions

<br>

--------------

<br>

## Disclaimer
This is not official software from Divoom.
It is a custom integration created by me (gickowtf) and therefore Divoom is not responsible for any damages/problems caused by this integration, nor does Divoom provide any end-user support for the integration.
Use this integration at your own risk.

<br>

--------------

<br>

## ❤️ Many thanks to
@Mrredstone5230 - Thanks for the conversion to config flow
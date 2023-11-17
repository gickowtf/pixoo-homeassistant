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

Now edit your configuration.yaml


### configuration.yaml example:
 Just a small example with the HA logo and the current time!

<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/solar.jpg?raw=true" title="Example of configuration.yaml Solar" align="left" height="150" />

```
divoom_pixoo:
  ip_address: 'CHANGEME'
  scan_interval:
    seconds: 15
  pages:
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
      ClockId:
        - number: 39
```

## all options for configuration.yaml

### Basic settings required

| **Keywords**  | **Values**                                                                   |
|:--------------|:-----------------------------------------------------------------------------|
| ip_address    | the IP address of Pixoo64 required                                           |
| scan_interval | to update the display or the time in seconds to jump from page to next page  |
| pages         | required                                                                     |
| page          | required numbered by integers                                                |

<br>

<img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/XY.png?raw=true" title="Example XY axis"  height="300" />

### Page setting, here you can be creative and insert as much text and images as you like.

| **Keywords**   | **Values**                                                                                 |
|:---------------|:-------------------------------------------------------------------------------------------|
| texts          | required                                                                                   |
| text           | Currently, only the status of a sensor is possible or a free text combined with the status |
| position       | The text position on a XY axis at 64x64 pixel                                              |
| font           | at this time there are two different Fonts FONT_GICKO and FONT_PICO_8                      |
| font_color     | RGB colors                                                                                 |
| images         | not required                                                                               |
| image          | Path to the image including file name .png preferred                                       |
| position       | The text position on a XY axis at 64x64 pixel                                              |

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


### Custom Channel - In Divoom app you can set three different custom channels which you can select here. 
| **Keywords**    | **Values**                                   |
|:----------------|:---------------------------------------------|
| channel         | Custom Channel in APP                        |
| number          | 0 = channel 1, 1 = channel 2, 2 = channel 3  |

<br>

### ClockId Channel - In Divoom app you can set three different custom channels which you can select here. 
| **Keywords** | **Values**         |
|:-------------|:-------------------|
| ClockId      | Clock Faces in APP |
| number       | int                |

If you have any further questions, I will be happy to help.

<br>

### Automation Example

You can use it for Push Notifications.
```
alias: Pixoo Notification
description: ""
trigger:
  - platform: state
    entity_id:
      - event.ANY-EVENT
condition: []
action:
  - service: divoom_pixoo.show_message
    data:
      entity_id: sensor.divoom_pixoo
      message: HELLO WORLD
      position: [0,0]
      color: [255, 0, 255]
      font: FONT_GICKO
mode: single
```

## Font
| **FONT**    | **IMAGE**                                                                                                                  |
|:------------|:---------------------------------------------------------------------------------------------------------------------------|
| FONT_GICKO  | <img src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/FONT_GICKO.png?raw=true" title="FONT_GICKO" />  |



## Issues

Sometimes the display crashes, especially with animated images. I have often read on the Internet that this is due to the power supply being too weak or the brightness being too high. I now have the display permanently set to **90%** and it no longer crashes.

## Discussions

I would be happy if you present your configuration.yaml in the Discussions area  
https://github.com/gickowtf/pixoo-homeassistant/discussions

## Disclaimer
This is not official software from Divoom.
It is a custom integration created by me (gickowtf) and therefore Divoom is not responsible for any damages/problems caused by this integration, nor does Divoom provide any end-user support for the integration.
Use this integration at your own risk.
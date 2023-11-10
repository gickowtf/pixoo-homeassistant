# Divoom Pixoo 64 Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/gickowtf)
![python badge](https://img.shields.io/badge/Made%20with-Python-orange)
![last commit](https://img.shields.io/github/last-commit/gickowtf/pixoo-homeassistant?color=red)

Custom component for easy use of a Pixoo64 within Home Assistant

## Installation
1. Install this integration with HACS (adding repository required), or copy the contents of this
repository into the `custom_components/pixoo-homeassistant` directory.
2. Restart Home Assistant.

Now edit your configuration.yaml


### configuration.yaml example:
 Just a small example with the HA logo and the current time!
<img src="images/example.jpg" title="Example of configuration.yaml" align="left" height="150" />

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
          time: "{{ states.sensor.YOUR_SENSOR.state }}"  #Formar HH:MM
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
```

### all options for configuration.yaml

| **options**     | **settings**                                                                               |
|:----------------|:-------------------------------------------------------------------------------------------|
| ip_address      | the IP address of Pixoo64 required                                                         |
| scan_interval   | to update the display or the time in seconds to jump from page to next page                |
| pages           | required                                                                                   |
|                 |                                                                                            |
| page            | required numbered by integers                                                              |
| texts           | required                                                                                   |
| text            | Currently, only the status of a sensor is possible or a free text combined with the status |
| position        | The text position on a XY axis at 64x64 pixel                                              |
| font            | at this time there are two different Fonts FONT_GICKO and FONT_PICO_8                      |
| font_color      | RGB colors                                                                                 |
| images          | not required                                                                               |
| image           | Path to the image including file name .png preferred                                       |
| position        | The text position on a XY axis at 64x64 pixel                                              |
|                 |                                                                                            |
| PV              | own designed PV stats                                                                      |
| power           | -required     use {{ template }}                                                           |
| storage         | -required     use {{ template }}                                                           |
| discharge       | -required     use {{ template }}                                                           |
| powerhousetotal | -required     use {{ template }}                                                           |
| vomNetz         | -required     use {{ template }}                                                           |
| time            | -required     use {{ template }}                                                           |
|                 |                                                                                            |
| channel         | Custom Channel in APP                                                                      |
| number          | 0 = channel 1, 1 = channel 2, 2 = channel 3                                                |

If you have any further questions, I will be happy to help.

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

## Issues

Sometimes the display crashes, especially with animated images. I have often read on the Internet that this is due to the power supply being too weak or the brightness being too high. I now have the display permanently set to **90%** and it no longer crashes.

## Discussions

I would be happy if you present your configuration.yaml in the Discussions area  
https://github.com/gickowtf/pixoo-homeassistant/discussions

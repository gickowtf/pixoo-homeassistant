<img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/logo.png?raw=true"  title="Example of configuration.yaml"  align="right"  height="90"  />

  

# Divoom Pixoo 64 Home Assistant Integration

  

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/gickowtf)
![python badge](https://img.shields.io/badge/Made%20with-Python-orange)
![last commit](https://img.shields.io/github/last-commit/gickowtf/pixoo-homeassistant?color=red)

  
  

Custom component for easy use of a Pixoo64 within Home Assistant. With this integration you have the possibility to display different designs and personalize them with information from the Home Assistant. For example, you can use this integration to display several texts {{ templates }} and images on one page. You can also use this integration to determine how long you want to see a page, e.g. you can set the page to change every 15 seconds. In addition, you also have a light entity for switching the display on and off or changing the brightness. Last but not least, you can create automations with which you can use certain triggers to display the pages that are available to you as a push.

  

## Installation

1. Install this integration with HACS (adding repository required), or copy the contents of this

repository into the `custom_components/divoom_pixoo` directory.

2. Restart Home Assistant.

3. Go to Settings / Integrations and add integration "Divoom Pixoo 64"

4. Please select a discovered Pixoo 64 device from the list or select 'Manual IP' to manually enter the device's IP.

  

## Configuration

  

### Base

*Settings > Devices > Divoom Pixoo > Configure*

  

**IP address of the device:** discovered or manually entered IP

  

**Scan interval (in seconds):** The amount of time a page is displayed

  

# Page Types & Configurations

  

Each page type will have configuration options unique to it. **All configs should be written using YAML**
*If you're new to this integration, we recommend starting with the components page type.*

In the YAML config, all pages are nested under `- page_type:`
When setting the default configuration. Multiple pages can be set. These will be rotated through using the time set in "scan interval"

**YAML Layout example**
```yaml
- page_type: channel
  id: 0
- page_type: clock
  id: 182
```
In addition, all page types can be dynamically set to Enable/Disable based on HA entities.


| **Config Options** | **required** | **Default** | **Values**                                                            | 
|--------------------|:------------:|:-----------:|-----------------------------------------------------------------------|
| enabled            |      F       |    true     | bool or {{ template }} *#expects  state = 'true', 'yes', 'on' or '1'* |

```yaml
- page_type: PAGE_TYPE
  enabled: "{{ states.input_boolean.YOURS.state }}"
```
## Page: Components
A components page  turns your Pixoo into your canvas!  You can tie multiple text/image configs to a single page.

```yaml
- page_type: components
  components:
    - type: text
      #[text config]
    - type: text
      #[text config]
    - type: image
      #[image config]
    - type: rectangle
      #[rectangle config]
```
<br>
*Note: Position X,Y coordinates will need to be manually configured for each component type*

#### XY Positioning

<img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/XY.png?raw=true"  title="Example XY axis"  height="300"  />

## Component Configurations
-type: [ text | image | rectangle ]

#### Component: Text

 
| **Config Options** | **required** | **Default** | **Values**                                                              | 
|--------------------|:------------:|-------------|-------------------------------------------------------------------------|
| position           |      T       |             | The text [position](#xy-positioning) on a XY axis at 64x64 pixel        |
| content            |      T       |             | Your message! *{{ templates }} and [Newline](#newline) Support in text* |
| font               |      F       | PICO_8      | [Fonts](#fonts)                                                         |
| color              |      F       | white       | [R, G, B] or [Colors](#color-presets)                                   |

  Example
```yaml
    - type: text
      position: [0,0]
      content: Welcome Home!
```  

#### Component: Image

| **Config Options** | **required** | **Default** | **Values**                                                                                                                         | 
|--------------------|:------------:|-------------|------------------------------------------------------------------------------------------------------------------------------------|
| position           |      T       |             | The text [position](#xy-positioning) on a XY axis at 64x64 pixel                                                                   |
| image_path         | T (pick one) |             | image path like /config/img/haus.png                                                                                               |
| image_url          | T (pick one) |             | image url like template {{ entity image }} or https://raw.githubusercontent.com/gickowtf/pixoo-homeassistant/main/images/pixoo.gif |
| image_data         | T (pick one) |             | image data in base64 convert images [here](https://base64.guru/converter/encode/image)                                             |
| height             |      F       |             | If none is selected, the image will be at it's original size. If one is selected, it will become the longest side. Proportional    |
| width              |      F       |             | If none is selected, the image will be at it's original size. If one is selected, it will become the longest side. Proportional    |
| resample_mode      |      F       | `box`       | `box`, `nearest`, `bilinear`, `hamming`, `bicubic`, `lanczos`                                                                      |

Example
```yaml
    - type: image
      position: [5,5]
      image_path: /config/image/haus.png
      resample_mode: box
      height: 64
```


#### Component: Rectangle

| **Config Options** | **required** | **Default** | **Values**                                                       | 
|--------------------|:------------:|-------------|------------------------------------------------------------------|
| position           |      T       |             | The text [position](#xy-positioning) on a XY axis at 64x64 pixel |
| size               |      T       |             | start position + size start                                      |
| color              |      T       |             | [Colors](#color-presets)                                         |
| filled             |      F       |             | boolean                                                          |

Example
```yaml
    - type: rectangle
      position: [20,  20]
      size: [10,  10]
      color: yellow
      filled: "{{ states.input_boolean.YOURS.state }}"  #optional
```



## Page: text [NOT RECOMMENDED]
*While you can use this page type, the components type is generally a better fit.*
\- page_type: text
 
| **Config Options** | **required** | **Default** | **Values**                                                              | 
|--------------------|:------------:|-------------|-------------------------------------------------------------------------|
| position           |      T       |             | The text [position](#xy-positioning) on a XY axis at 64x64 pixel        |
| content            |      T       |             | Your message! *{{ templates }} and [Newline](#newline) Support in text* |
| font               |      F       | PICO_8      | [Fonts](#fonts)                                                         |
| color              |      F       | white       | [R, G, B] or [Colors](#color-presets)                                   |

```yaml
- page_type: text
  position: [0,0] 
  content: Welcome Home!
```

## Page: Channel
*In Divoom app you can set three different custom channels which you can select here.*
*Note: The Divoom custom channel pic cycle rate must be set in the app itself*
  \- page_type: channel

 - Channel 1 = `id: 0`
 - Channel 2 = `id: 1`
 - Channel 3 = `id: 2`


| **Config Options** | **required** | **Default** | **Values** | 
|--------------------|:------------:|-------------|------------|
| id                 |      T       |             | Integer    |

Example:
```yaml
- page_type: channel
  id: 0
```


## Page: Clock
*In Divoom app you can set three different custom channels which you can select here.*

  \- page_type: clock


| **Config Options** | **required** | **Default** | **Values**                                                                                                 | 
|--------------------|:------------:|-------------|------------------------------------------------------------------------------------------------------------|
| id                 |      T       |             | Clock ID [list of clock ID's](https://github.com/gickowtf/pixoo-homeassistant/blob/main/READMES/CLOCKS.md) |

Example:
```yaml
- page_type: clock
  id: 182
```
 
 

  
### Alternative Method to find ClockFace ID's

1. Navigate to settings > integrations > Divoom Pixoo 64 
2. Activate debug logging
3. Open the Divoom app on your smartphone and select your preferred ClockFace.
4. As soon as this is displayed on your Pixoo64, you will find "Device Data" in the log and then "CurClockId".
5. The CurClockId is the number you were looking for.

## Page: Visualizer
This adds the visualizer page to the integration. 
<br>

| **Config Options** | **required** | **Default** | **Values**              | 
|--------------------|:------------:|-------------|-------------------------|
| id                 |      T       |             | Clock (visualizer) ID   | 

<br>

*The id starts at zero and it represents the clocks from top left to bottom right as can be seen in the app.*

Example: 

```yaml
- page_type: visualizer
  id: 2
```

<img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/visualizer.png?raw=true" height="400"  width="400"  />

## Page: PV
Photovoltaic - PV is a pre-designed page. The icon changes depending on the battery capacity and the font color changes from red to green
*Helper entities may have to be used here*

<img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/pixoo.gif?raw=true"  title="Example of configuration.yaml Solar"  align="left"  height="150"  width="150"  />

```yaml 
- page_type: PV
  enabled: "{{ states.input_boolean.YOURS.state }}"  #is only displayed if the state = 'true', 'yes', 'on' or '1'
  power: "{{ states.sensor.YOUR_SENSOR.state }}"
  storage: "{{ states.sensor.YOUR_SENSOR.state }}"
  discharge: "{{ states.sensor.YOUR_SENSOR.state }}"
  powerhousetotal: "{{ states.sensor.YOUR_SENSOR.state }}"
  vomNetz: "{{ states.sensor.YOUR_SENSOR.state }}"
  time: "{{ now().strftime('%H:%M') }}"
```
## Page: Progress Bar
 *Special page with a progress bar for, for example, the status of the dishwasher or charging status of the car*
 
 \- page_type: progress_bar
  
  
<img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/progressbar.png?raw=true"  title="Example of configuration.yaml ProgressBar"  align="left"  height="150"  />

| **Config Options**  | **required** | **Default** | **Values**                                       | 
|---------------------|:------------:|-------------|--------------------------------------------------|
| header              |      T       |             | string or use {{ template }}  *e.g. Dishwasher*  |
| progress            |      T       |             | integer or use {{ template }}                    |
| footer              |      T       |             | string or use {{ template }}  *e.g. Date*        |
| bg_color            |      F       | blue        | use "[R, G, B]" or [Colors](#color-presets)      |
| header_offset       |      F       | 2           | integer                                          |
| header_font_color   |      F       | white       | use "[R, G, B]" or [Colors](#color-presets)      |
| progress_bar_color  |      F       | red         | use "[R, G, B]" or [Colors](#color-presets)      |
| progress_text_color |      F       | white       | use "[R, G, B]" or [Colors](#color-presets)      |
| time_color          |      F       | grey        | use "[R, G, B]" or [Colors](#color-presets)      |
| footer_offset       |      F       | 2           | integer                                          |
| footer_font_color   |      F       | white       | use "[R, G, B]" or [Colors](#color-presets)      |

Example:

```yaml
- page_type: progress_bar
  enabled: >-
  {% if is_state('sensor.DISHWASCHER_STATE', 'Run') %} true {% else %} false {% endif %}
  header: DISHWASHER
  progress: "{{ states.sensor.DISHWASHER_PROGRESS.state }}"
  footer: ANY FOOTER
  header_font_color: "[255, 255, 255]"
```

## Page: Fuel
*Special Page for Gas Station Pricing. Helper entities may have to be used here*
 
 \- page_type: fuel
  
  
<img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/gasstation.jpg?raw=true"  title="Example of configuration.yaml Solar"  />

<br>

| **Config Options** | **required** | **Default**          | **Values**                                                                   | 
|--------------------|:------------:|----------------------|------------------------------------------------------------------------------|
| title              |      T       |                      | string - can use {{ template }}  e.g. Gas Station Name                       |
| name1              |      T       |                      | string - can use {{ template }} *e.g. fuel type*                             |   
| price1             |      T       |                      | use {{ template }}   *e.g. fuel price*                                       |  
| name2              |      T       |                      | string - can use {{ template }}                                              |   
| price2             |      T       |                      | use {{ template }}                                                           |   
| name3              |      T       |                      | string - can use {{ template }}                                              |       
| price3             |      T       |                      | use {{ template }} eg. fuel price                                            |
| status             |      T       |                      | string - can use {{ template }} Any extra field in my case an opening status |
|                    |              |                      |                                                                              |
| font_color         |      F       | white                | "[R, G, B]" or [Colors](#color-presets)                                      |       
| bg_color           |      F       | yellow (255, 230, 0) | "[R, G, B]" or [Colors](#color-presets)                                      |              
| price_color        |      F       | white                | "[R, G, B]" or [Colors](#color-presets)                                      |
| title_color        |      F       | black                | "[R, G, B]" or [Colors](#color-presets)                                      |
| stripe_color       |      F       | font_color           | "[R, G, B]" or [Colors](#color-presets)                                      |         
| title_offset       |      F       | 2                    | integer *used to center the text*                                            |

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


--------------
### Newline

  

**Newline Support** in `content:` example:

```yaml
content: |-
text 1
{{ states.*.state }}
```

*There is no limit to the maximum newlines except for 64 pixels ;)*
  

# Services

  
  

## Service: Send a page to Divoom Pixoo (show_message) Push Notification

  

You can use it for Push Notifications. Trigger with anything! Call it with the Service "Divoom Pixoo 64: Send a page to Divoom Pixoo".

You can input in the _Page Data_ field the data of **one** page in the normal YAML format. It can be anything! 

*Note: This is intended to be a temporary override of your default configuration. Any Enable/disable lines will not be respected here.*

  

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
    position: [10,  0]
    content: 2 github/gickowtf
    font: PICO_8
    color: [255,  0,  0]
  - type: image
    image_path: /config/img/haus.png
    position: [30,  30]
```

  



## Service: Play a Buzzer

Play the buzzer on the Divoom Pixoo. Beware that this maybe could damage the device. Use at your own risk.

  
  
**Buzzing Time per cycle.** in milliseconds `default: 500 milliseconds`<br>

*The working time of the buzzer per cycle. The buzzer will not buzz continuously; it will go on and off in cycles (duration in-between not controllable).*

**Idle Time per cycle** in milliseconds `default: 500 milliseconds`<br>

*Idle time of the buzzer per cycle.*

  

**Total Time** in milliseconds `default: 3000 milliseconds`<br>

*The total time the buzzer will be working.*

  

<br>

 
## Service: Restart the Divoom Pixoo


Restart the Divoom Pixoo device. (It has a little bit of delay. Be patient.)

  
  

<br>

  
--------------

# Templates (entity states)

As mentioned above, templates allow you to bring Entity states and attributes directly to your Pixoo! (eg. Temperature, brightness, presence, entity on/off). *For a deep dive see [HA config link]*

  

You can find the entity ID in HA under Developer > States

  

## Report Raw Sensor Readings

  

Binary sensors are the easiest to start with, as they simply live in one of two states, On or Off.

```yaml
- page_type: components
  components:
    - type: text
      font: PICO_8
      position: [0,0]
      color: white
      content: >-
      Motion-FL1: {{ states('binary_sensor.MotionDetector' }}
```

  

In the above example, the Pixoo would display

"Motion-FL1: [on/off]

  

## Conditionally replacing text based on sensor readings

  
  

What if you want to change *on -> detected* and *off -> clear*?

  

One way is to use a combination of If/then/else (short form below) and a state comparator (is_state)

  

```yaml
content: >-
Motion-FL1: {{ 'Detected' if
is_state('binary_sensor.MotionDetector', ['on']) else
'clear' }}
```

You might say "well that's pretty nifty, but I also want to dynamically change the color because *a e s t h e t i c s*.

  

Well I've got great news for you!

  

## Using templates to dynamically change text color

We can take the exact same concept used for the text, and apply it to color. All we need to do is swap text for color codes.

  

If Motion Detected, color = red *(255,0,0)*; else color = green (0,255,0)

  
 ```yaml
color: >-
{{ [255,0,0] if is_state('binary_sensor.motionDetector',
['on']) else [0,255,0] }}
```

## Example: Animations through automations 
Note: In this example we're using a count helper to act as a countdown

```yaml
alias: pixoo64 - auto-ani
description: ""
trigger: []
condition: []
action:
  - service: counter.reset
    metadata: {}
    data: {}
    target:
      entity_id: counter.pixoo_5s_count_down
  - repeat:
      count: 20
      sequence:
        - service: divoom_pixoo.show_message
          target:
            entity_id: sensor.divoom_pixoo_64_current_page
          data:
            page_data:
              page_type: components
              components:
                - type: text
                  position:
                    - 0
                    - 30
                  content: "Auth Check in: {{ states('counter.pixoo_5s_count_down') }}"
                  font: PICO_8
                  color: white
                - type: image
                  image_url: https://pub.inflowbogie.dev/lock_closed.png
                  position:
                    - 0
                    - 40
                  resample_mode: box
                  height: 20
                - type: image
                  image_url: https://pub.inflowbogie.dev/key.png
                  position:
                    - "{{ 2 * states('counter.pixoo_5s_count_down') }}"
                    - 50
                  resample_mode: box
                  height: 7
        - service: counter.decrement
          metadata: {}
          data: {}
          target:
            entity_id: counter.pixoo_5s_count_down
        - delay:
            hours: 0
            minutes: 0
            seconds: 1
            milliseconds: 0
        - if:
            - condition: state
              entity_id: counter.pixoo_5s_count_down
              state: "0"
          then:
            - service: counter.reset
              metadata: {}
              data: {}
              target:
                entity_id: counter.pixoo_5s_count_down
mode: single

```


![animated](https://pub.inflowbogie.dev/authCheck.gif) 

# References

## Fonts

| Font     | Image                                                                                                                                     |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------|
| GICKO    | <img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/FONT_GICKO.png?raw=true"  title="FONT_GICKO"  width="500"  /> |
| FIVE_PIX | <img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/five_pix.png?raw=true"  title="five_pix"  width="500"  />     |
| PICO_8   | <img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/PICO_8.png?raw=true"  title="PICO_8"  width="500"  />         |

  

<br>

  

--------------

  

## Color Presets
The colors in this chart can be used as presets to replace the [R,G,B] color coding.

<img  src="https://github.com/gickowtf/pixoo-homeassistant/blob/main/images/colors.png?raw=true"  title="colors"  />

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

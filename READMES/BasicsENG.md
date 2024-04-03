# Basics

In this part I will go into more detail, but I think once this is understood you can use all the possibilities with the Pixoo integration.

I have created an extra sensor `sensor.example` for the example.
![devtools.jpg](images%2Fdevtools.jpg)

> The sensor has the `State` 1337 which can be addressed with the Jinja template engine as follows:
<br>`{{ states("sensor.example") }}` which results in the following output: `1337`.


You can check this in the `Template` tab in the developer tools.

![template_editor.jpg](images%2Ftemplate_editor.jpg)

So if we want to output the state of the sensor `sensor.example` on our Pixoo display, we can achieve this with the following code:
Navigate to `Settings / Devices and Services / Integration / Divoom Pixoo 64` and then to `Configure`.

![configure.jpg](images%2Fconfigure.jpg)

```yaml
- page_type: components
  components:
    - type: text
      position: [0, 0]
      content: "{{ states('sensor.example') }}"
```

The output on the display then looks as follows:

![1337_preview.png](images%2F1337_preview.png)

Okay, that's the first success!

>Next, we adjust the position, text color and font:<br>
The individual colors and possible fonts are described in the [Readme](https://github.com/gickowtf/pixoo-homeassistant). Colors can also be specified as [R, G, B].
```yaml
- page_type: components
  components:
    - type: text
      position: [10, 20] # 10 = von links nach rechts und 20 von oben nach unten versetzt
      content: "{{ states('sensor.example') }}"
      font: gicko
      color: yellow
```
Let's add an image in the next step.<br>
Images can be inserted from a URL, path or as Base64 [Image Readme](https://github.com/gickowtf/pixoo-homeassistant?tab=readme-ov-file#component-image)

In our example, we use `image_path` as the image is already present in the installation of the integration.

```yaml
- page_type: components
  components:
    - type: text
      position: [10, 20] # 10 = von links nach rechts und 20 von oben nach unten versetzt
      content: "{{ states('sensor.example') }}"
      font: gicko
      color: yellow
    - type: image
      position: [5,5]
      image_path: "/config/custom_components/divoom_pixoo/img/haus.png"
      resample_mode: box
      height: 64
```

Next, we insert a `rectangle` and go to layering.
[Rectangle Readme](/config/custom_components/divoom_pixoo/img)

In the first example, we deliberately write the `- type: rectangle` last in the configuration.
```yaml
- page_type: components
  components:
    - type: text
      position: [10, 20] # 10 = von links nach rechts und 20 von oben nach unten versetzt
      content: "{{ states('sensor.example') }}"
      font: gicko
      color: yellow
    - type: image
      position: [5,5]
      image_path: "/config/custom_components/divoom_pixoo/img/haus.png"
      resample_mode: box
      height: 64
    - type: rectangle
      position: [5,5]
      size: [30,  30]
      color: red
```
> What happened? The red square covers the text and the image because the config was read synchronously from top to bottom. Thus the red square was also added last and now covers the text and image.<br>

The solution is now layering. If we want to have the red square as the background of the image and text, we should first write this in the config.

```yaml
- page_type: components
  components:
    - type: rectangle
      position: [5,5]
      size: [30,  30]
      color: red
    - type: text
      position: [10, 20] # 10 = von links nach rechts und 20 von oben nach unten versetzt
      content: "{{ states('sensor.example') }}"
      font: gicko
      color: yellow
    - type: image
      position: [5,5]
      image_path: "/config/custom_components/divoom_pixoo/img/haus.png"
      resample_mode: box
      height: 64
```
Well, I hope I've been able to give you a better understanding so far. Now it's up to your creativity!

Next, I would like to talk about different pages. After all, it would be boring if the display only showed one page at a time.

Example with our created page and a ClockFace that change in a time interval of 15 seconds.

```yaml
- page_type: components
  components:
    - type: rectangle
      position: [5,5]
      size: [30,  30]
      color: red
    - type: text
      position: [10, 20] # 10 = von links nach rechts und 20 von oben nach unten versetzt
      content: "{{ states('sensor.example') }}"
      font: gicko
      color: yellow
    - type: image
      position: [5,5]
      image_path: "/config/custom_components/divoom_pixoo/img/haus.png"
      resample_mode: box
      height: 64
- page_type: clock
  id: 182
```

>Ok, now there are situations where I want to see pages longer or shorter for this there is the `duration` tag.

```yaml
- page_type: components
  duration: 30
  components:
    - type: text
      position: [10, 20]
      content: "30 sekunden"
      font: gicko
      color: yellow
- page_type: clock
  duration: 10 # sekunden
  id: 182
```

The `page_type: components` is now displayed for 30 seconds and the `page_type: clock` for only 10 seconds.

Next, there may be situations in which pages should only be displayed under certain conditions. For this there is the `enabled` tag.

For this we use jinja templates again. 
In this example we ask if the `state` of the sensor.example = 1337 and get a `true` back because the condition is true
```yaml
{% if is_state('sensor.example', '1337') %} True {%else %} False {% endif %}
```
or simplified:
```yaml
{{ is_state('sensor.example', '1337') }}
```

If we now use this in our config, only the `page_type: clock` is displayed as this is `true`. 
```yaml
- page_type: components
  enabled: "{{ is_state('sensor.example', '1338') }}" #false
  duration: 30
  components:
    - type: text
      position: [10, 20]
      content: "30 sekunden"
      font: gicko
      color: yellow
- page_type: clock
  enabled: "{{ is_state('sensor.example', '1337') }}" #true
  duration: 10 # sekunden
  id: 182
```

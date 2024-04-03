# Photovoltaics page/ Solaranlage


## With Battery / mit Batterie
![solar.png](..%2Fimages%2Fsolar.png)

[DE] Im oberen Teil der YAML konfiguration müssen die Variablen `power`, `storage`, `discharge`, `powerhousetotal`, `gridpower` angepasst werden. Ausserdem gegebenfalls `time`.

[ENG] In the upper part of the YAML configuration, the variables `power`, `storage`, `discharge`, `powerhousetotal`, `gridpower` must be adjusted. Also `time` if necessary.
```yaml
- page_type: components
  variables:
    power: "{{ states('sensor') }}"
    storage: "{{ states('sensor') }}" #percentage
    discharge: "{{ states('sensor') }}"
    powerhousetotal: "{{ states('sensor') }}"
    gridpower: "{{ states('sensor') }}"
    time: "{{ now().strftime('%H:%M') }}"
  components:
  - type: image
    image_path: "/config/custom_components/divoom_pixoo/img/sunpower.png"
    position: [2,1]
  - type: text
    content: "{{ power }}"
    color: "{{ [255,175,0] if power|int >= 1 else [131,131,131] }}"
    font: GICKO
    position: [17,8]
  - type: image
    image_path: "{{ '/config/custom_components/divoom_pixoo/img/akku80-100.png' if storage|int >= 80 else '/config/custom_components/divoom_pixoo/img/akku60-80.png' if storage|int >= 60 else '/config/custom_components/divoom_pixoo/img/akku40-60.png' if storage|int >= 40 else '/config/custom_components/divoom_pixoo/img/akku20-40.png' if storage|int >= 20 else '/config/custom_components/divoom_pixoo/img/akku00-20.png'}}"
    position: [2, 17]
  - type: text
    content: "{{ discharge }}"
    color: "{{ [255,0,68] if discharge|int <= 0 else [4,204,2] }}"
    font: GICKO
    position: [17, 18]
  - type: text
    content: "{{ storage }}%"
    color: white
    font: PICO_8
    position: [17, 25]
  - type: image
    image_path: "/config/custom_components/divoom_pixoo/img/haus.png"
    position: [2,33]
  - type: text
    content: "{{ powerhousetotal }}"
    color: [0,123,255]
    font: GICKO
    position: [17, 40]
  - type: image
    image_path: "/config/custom_components/divoom_pixoo/img/industry.png"
    position: [2,49]
  - type: text
    content: "{{ gridpower }}"
    color: [131,131,131]
    font: GICKO
    position: [17, 56]
  - type: text
    content: "{{ time }}"
    color: white
    font: PICO_8
    position: [44, 1]
```
## Without Battery / Ohne Batterie
[DE] Sollte man die Anzeige ohne Batterie Anzeige benötigen so könne man den folgen YAML Code verwenden.

[ENG] If you need the display without battery display, you can use the following YAML code.
![solar_withoutBattery.png](..%2Fimages%2Fsolar_withoutBattery.png)
```yaml
- page_type: components
  variables:
    power: "{{ states('sensor') }}"
    storage: "{{ states('sensor') }}" #percentage
    discharge: "{{ states('sensor') }}"
    powerhousetotal: "{{ states('sensor') }}"
    gridpower: "{{ states('sensor') }}"
    time: "{{ now().strftime('%H:%M') }}"
  components:
  - type: image
    image_path: "/config/custom_components/divoom_pixoo/img/sunpower.png"
    position: [2,17]
  - type: text
    content: "{{ power }}"
    color: "{{ [255,175,0] if power|int >= 1 else [131,131,131] }}"
    font: GICKO
    position: [17,24]
  - type: image
    image_path: "/config/custom_components/divoom_pixoo/img/haus.png"
    position: [2,33]
  - type: text
    content: "{{ powerhousetotal }}"
    color: [0,123,255]
    font: GICKO
    position: [17, 40]
  - type: image
    image_path: "/config/custom_components/divoom_pixoo/img/industry.png"
    position: [2,49]
  - type: text
    content: "{{ gridpower }}"
    color: [131,131,131]
    font: GICKO
    position: [17, 56]
  - type: text
    content: "{{ time }}"
    color: white
    font: clock
    position: [15, 2]
```
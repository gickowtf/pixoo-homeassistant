# Basics

In diesem Teil werde ich etwas weiter ausholen aber ich denke wenn dies verstanden ist kann man mit der Pixoo Integration alle möglichkeiten ausnutzen.

Für das Beispiel habe ich ein extra sensor `sensor.example` erstellt.
![devtools.jpg](images%2Fdevtools.jpg)

> Der Sensor hat den `State` 1337 diesen kann man mit der Jinja template Engine wie folgt ansprechen:
<br>`{{ states("sensor.example") }}` was die folgende ausgabe: `1337` ergibt.


In den Entwickler tools kann man dies im Tab `Template` überprüfen.

![template_editor.jpg](images%2Ftemplate_editor.jpg)

Wenn wir also den State des sensors `sensor.example` auf unserem Pixoo Display ausgeben wollen können wir dies mit folgendem Code erreichen:
Navigiere dazu in die `Einstellungen / Geräte und Dienste / Integration / Divoom Pixoo 64` und dann auf `Konfigurieren`

![configure.jpg](images%2Fconfigure.jpg)

```yaml
- page_type: components
  components:
    - type: text
      position: [0, 0]
      content: "{{ states('sensor.example') }}"
```

Die ausgabe auf dem Display sieht dann wie folgt aus:

![1337_preview.png](images%2F1337_preview.png)

Okay das ist der erste Erfolg!

>Als nächstes passen wir die Position, Textfarbe und Font an:<br>
Die einzelnen Farben und möglichen Fonts sind in der [Readme](https://github.com/gickowtf/pixoo-homeassistant) beschrieben. Farben kann man auch als [R, G, B] angeben.
```yaml
- page_type: components
  components:
    - type: text
      position: [10, 20] # 10 = von links nach rechts und 20 von oben nach unten versetzt
      content: "{{ states('sensor.example') }}"
      font: gicko
      color: yellow
```
Fügen wir im nächsten Schritt ein Bild hinzu.<br>
Bilder können von einer URL, Pfad oder als Base64 eingefügt werden [Image Readme](https://github.com/gickowtf/pixoo-homeassistant?tab=readme-ov-file#component-image)

In unserem Beispiel nutzen wir `image_path` da das Bild bereits in der Installation der Integration vorhanden ist.

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

Als nächstes fügen wir ein `rectangle` ein und gehen auf layering (Ebenen) ein.
[Rectangle Readme](/config/custom_components/divoom_pixoo/img)

Im ersten Beispiel schreiben wir bewusst als letzte den `- type: rectangle` in die configuration.
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
> Was ist passiert? Das Rote Viereck verdeckt den text und das bild weil die config synchron von oben nach unten gelesen wurde. Somit wurde das Rote Viereck auch zuletzt hinzugefügt und verdeckt nun text und bild.<br>

Die Lösung ist nun das Layering. Wenn wir das Rote Viereck als Hintergrund von Bild und Text haben wollen sollten wir dies auch zuerst in die Config schreiben.

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
Nun ich hoffe ich konnte dir bis hierhin einiges näher bringen. Jetzt liegt es letztendlich an deiner Kreativität!

Als nächstes möchte ich auf verschiedene Seiten eingehen. Es wäre schliesslich langweilig wenn das Display immer nur eine Seite anzeigen würde.

Beispiel mit unserer erstellten Seite und einem ClockFace die in einem Zeit interval von 15 sekunden wechseln.

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

>Ok, nun gibt es Situation wo ich Seiten länger oder kürzer sehen möchte dafür gibt es den `duration` tag.

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

Der `page_type: components` wird nun 30 sekunden angezeigt und der `page_type: clock` nur 10 sekunden.

Als nächste gibt es vielleicht Situation in der Seiten nur zu bestimmten Bedingungen angezeigt werden sollen. Hierzu gibt es das `enabled` tag.

Hierzu nutzen wir wieder jinja templates. 
Wir fragen in diesem Beispiel ab ob der `state` des sensor.example = 1337 ist und bekommen folglich ein `true` zurück da die bedingung zutrifft
```yaml
{% if is_state('sensor.example', '1337') %} True {%else %} False {% endif %}
```
oder stark vereinfacht:
```yaml
{{ is_state('sensor.example', '1337') }}
```

nutzen wir dies nun in unserer config, so wird nur noch der `page_type: clock` angezeigt da dieser `true` ist. 
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

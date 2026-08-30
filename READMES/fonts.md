# Fonts & Typography

This guide shows how to use the bundled pixel fonts and how to add your own custom Adobe BDF bitmap fonts to your Pixoo 64 dashboard.

---

## 1. Bundled BDF Pixel Fonts

These fonts are included out-of-the-box with the integration:

### A. Tiny5 (5px Proportional)
Ultra-compact font supporting broad Western & Central European Latin, Cyrillic, fractions (`¼ ½ ¾`), directional arrows (`← ↑ → ↓`), Bitcoin (`₿`), currencies (`€ £ ¥ ¢ $`), math (`° ± × ÷`), and symbols (`© ® ™`).

```yaml
- page_type: components
  enabled: true
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
      filled: true
    - type: text
      position: [32, 8]
      align: center
      color: cyan
      font: Tiny5
      content: "Tiny5 (5px)"
    - type: text
      position: [32, 20]
      align: center
      color: white
      font: Tiny5
      content: "The Quick Brown Fox"
    - type: text
      position: [32, 32]
      align: center
      color: yellow
      font: Tiny5
      content: "0123456789  23.5°C"
    - type: text
      position: [32, 44]
      align: center
      color: lime
      font: Tiny5
      content: "₿ € £  ← ↑ → ↓  ½"
```

### B. Pixelify Sans (7px Proportional)
Modern, highly legible pixel font (570+ glyphs) supporting full Western European Latin (`Á À Ä é ñ ç`), Cyrillic (`А-Я`, `а-я`), currencies (`€ £ ¥`), and math symbols (`± ×`).

```yaml
- page_type: components
  enabled: true
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
      filled: true
    - type: text
      position: [32, 8]
      align: center
      color: cyan
      font: PixelifySans
      content: "Pixelify (7px)"
    - type: text
      position: [32, 22]
      align: center
      color: white
      font: PixelifySans
      content: "Smooth Proportional"
    - type: text
      position: [32, 36]
      align: center
      color: yellow
      font: PixelifySans
      content: "0123456789"
    - type: text
      position: [32, 50]
      align: center
      color: magenta
      font: PixelifySans
      content: "Á é ñ ç  Ж я  € £"
```

### C. Press Start 2P (8px Monospace)
Classic 8-bit arcade font. Each character has a fixed 8px advance (fits exactly 8 characters per line across a 64x64 screen). Supports Latin, Greek, Cyrillic, and retro gaming symbols like star (`★` `\u2605`), heart (`♥` `\u2665`), and arrows (`← ↑ → ↓`).

```yaml
- page_type: components
  enabled: true
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
      filled: true
    - type: text
      position: [32, 8]
      align: center
      color: cyan
      font: PressStart2P
      content: "PRESS 12"
    - type: text
      position: [32, 22]
      align: center
      color: yellow
      font: PressStart2P
      content: "START 34"
    - type: text
      position: [32, 36]
      align: center
      color: lime
      font: PressStart2P
      content: "1UP★  ♥"
    - type: text
      position: [32, 50]
      align: center
      color: orange
      font: PressStart2P
      content: "GAME OVER"
```

### D. PICO_8 (3x5 / 4px Monospace)
Official PICO-8 console font supporting 3x5 uppercase (`A–Z`), 3x4 small-caps (`a–z`), numbers, Katakana, directional arrows (`← ↑ → ↓`), and retro game symbols including heart (`♥` `\u2665`), star (`★` `\u2605`), music note (`♪` `\u266A`), diamond (`◆` `\u25C6`), house/castle (`⌂` `\u2302`), and D-Pad buttons (`⬅ ➡ ⬆ ⬇`).

```yaml
- page_type: components
  enabled: true
  components:
    - type: rectangle
      position: [0, 0]
      size: [64, 64]
      color: black
      filled: true
    - type: text
      position: [32, 10]
      align: center
      color: cyan
      font: PICO_8
      content: "PICO-8 CONSOLE"
    - type: text
      position: [32, 24]
      align: center
      color: white
      font: PICO_8
      content: "tiny pixel font"
    - type: text
      position: [32, 38]
      align: center
      color: yellow
      font: PICO_8
      content: "0123456789"
    - type: text
      position: [32, 50]
      align: center
      color: lime
      font: PICO_8
      content: "1UP  SCORE 9990"
```

#### Mapped Unicode Characters for PICO-8 (Copy & Paste)
Here are the mapped Unicode characters that can be used in `PICO_8`:

* **Arrows & Controls:** ←↑→↓◀▶⬅➡⬆⬇
* **Icons & Shapes:** ♥★♪◆○●■□⌂☉✽❎⧗█░▒▤▥▮◜◝‖•…⁘⁙∧웃
* **Accents & Symbols:** ¥°×ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙ
* **Katakana:** アイウエオカキクケコサシスセソタチッツテトナニヌネノハヒフヘホマミムメモャヤュユョヨラリルレロワヲン
* **Hiragana:** あいうえおかきくけこさしすせそたちっつてとなにぬねのはひふへほまみむめもゃやゅゆょよらりるれろゎわをん゛゜
* **Japanese Punctuation:** 、。「」

---

## 2. Built-in Bit-Matrix Fonts (A–Z, a–z, 0–9)

Hardcoded bitmap fonts for standard English text, clock faces, and countdowns:

* **`five_pix`:** 5x5 uppercase (A–Z), lowercase (a–z), 0–9, and punctuation (`. , ! ? - / °`).
* **`gicko`:** 6x6 uppercase (A–Z), 0–9, and symbols (lowercase automatically converts to uppercase).
* **`eleven_pix`:** 11px tall uppercase headers (A–Z) and large numbers (0–9).
* **`clock`:** Specialized digital clock numbers (0–9) and colon (`:`).

---

## 3. Adding Custom BDF Fonts

You can add any standard Adobe BDF bitmap font to your Home Assistant instance without modifying any integration code:

1. Create a `fonts/` folder in your Home Assistant configuration directory:
   ```bash
   mkdir -p /config/fonts
   ```
   *(The integration automatically scans `/config/fonts`, `custom_components/divoom_pixoo/fonts`, and `/config/esphome/fonts`)*.
2. Drop your `.bdf` file into `/config/fonts/` (e.g. `unifont.bdf` or `MinecraftDefault.bdf`).
3. Reference it directly by its filename (case-insensitive) in any component:
   ```yaml
   - type: text
     position: [0, 10]
     font: unifont
     content: "★ ⚡ ☕ ❄ ❤"
   ```

> **Memory Optimization:** Custom BDF fonts are indexed at startup and loaded into RAM on-demand only when a page actually uses them. Unused fonts consume zero active memory.

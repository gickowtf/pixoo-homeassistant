import os
import sys
import unittest
from unittest.mock import MagicMock

for mod in [
    "requests", "PIL", "homeassistant", "homeassistant.config_entries",
    "homeassistant.core", "homeassistant.exceptions", "homeassistant.helpers",
    "homeassistant.helpers.template", "homeassistant.helpers.entity", "homeassistant.components"
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from custom_components.divoom_pixoo.pixoo64._bdf import FontManager
from custom_components.divoom_pixoo.pixoo64._pixoo import Pixoo


class TestBdfFonts(unittest.TestCase):

    def setUp(self):
        fonts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "custom_components",
            "divoom_pixoo",
            "fonts",
        )
        self.fm = FontManager([fonts_dir])
        self.pixoo = Pixoo("127.0.0.1", size=64)

    def test_font_lookups(self):
        """Test retrieving fonts by name with case-insensitivity and fallback."""
        for font_name in ["PICO_8", "pico_8", "Tiny5", "five_pix", "gicko"]:
            font = self.fm.get_font(font_name)
            self.assertIsNotNone(font)
            self.assertGreater(font.get_text_width("TEST"), 0)

        # Fallback on unknown font
        self.assertIsNotNone(self.fm.get_font("nonexistent_font", fallback=True))

    def test_text_rendering(self):
        """Test measuring and drawing text on the canvas."""
        font = self.fm.get_font("Tiny5")
        self.assertGreater(self.pixoo.get_text_width("Hello", font), 0)

        self.pixoo.clear()
        self.pixoo.draw_text("Hello World", (0, 0), (255, 255, 255), font)


if __name__ == '__main__':
    unittest.main()

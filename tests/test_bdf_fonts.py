import os
import sys
import unittest
from unittest.mock import MagicMock

# Mock uninstalled dependencies for standalone testing
for mod in [
    "requests", "PIL", "homeassistant", "homeassistant.config_entries",
    "homeassistant.core", "homeassistant.exceptions", "homeassistant.helpers",
    "homeassistant.helpers.template", "homeassistant.helpers.entity", "homeassistant.components"
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from custom_components.divoom_pixoo.pixoo64._bdf import BdfFont, SpriteFont, FontManager, load_bdf_font
from custom_components.divoom_pixoo.pixoo64._font import FONT_PICO_8, FONT_GICKO
from custom_components.divoom_pixoo.pixoo64._pixoo import Pixoo


class TestBdfFonts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fonts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "custom_components",
            "divoom_pixoo",
            "fonts",
        )
        cls.tiny5_path = os.path.join(cls.fonts_dir, "Tiny5.bdf")

    def test_bdf_font_loading_and_metrics(self):
        """Test loading Tiny5.bdf and verifying metrics and glyphs."""
        data = load_bdf_font(self.tiny5_path)
        self.assertIsNotNone(data)
        font = BdfFont("Tiny5", data, self.tiny5_path)

        self.assertTrue(font.supports("A"))
        self.assertTrue(font.supports("’"))
        self.assertEqual(5, font.get_char_width("A"))
        self.assertEqual(2, font.get_char_width(" "))
        self.assertEqual(font.get_char_width("A") * 2, font.get_text_width("AA"))

    def test_font_manager_lazy_lookups(self):
        """Test case-insensitive lookups, lazy on-demand loading, and sprite font wrapping."""
        fm = FontManager([self.fonts_dir])

        # Sprite font lookups (case-insensitive)
        pico8 = fm.get_font("pico_8")
        self.assertIsNotNone(pico8)
        self.assertIs(pico8, fm.get_font("PICO_8"))
        self.assertEqual(3, pico8.get_char_width("A"))

        # BDF lazy loading: indexed first, loaded into RAM on get_font
        self.assertIn("tiny5", fm._available_bdf_files)
        self.assertNotIn("tiny5", fm._fonts)
        tiny5 = fm.get_font("tiny5")
        self.assertIsNotNone(tiny5)
        self.assertIn("tiny5", fm._fonts)
        self.assertIs(tiny5, fm.get_font("TINY5"))

        # Fallback
        self.assertEqual(pico8, fm.get_font("nonexistent_font", fallback=True))

    def test_pixoo_draw_text(self):
        """Test Pixoo draw_text and width calculations with both BDF and sprite fonts."""
        pixoo = Pixoo("127.0.0.1", size=64)
        fm = FontManager([self.fonts_dir])

        tiny5 = fm.get_font("tiny5")
        pico8 = fm.get_font("pico_8")

        self.assertEqual(tiny5.get_text_width("HELLO"), pixoo.get_text_width("HELLO", tiny5))
        self.assertEqual(pico8.get_text_width("HELLO"), pixoo.get_text_width("HELLO", pico8))

        # Ensure lowercase strings automatically uppercase for uppercase-only sprite fonts (e.g. GICKO)
        gicko = fm.get_font("gicko")
        self.assertTrue(gicko.supports("a"))
        self.assertEqual(FONT_GICKO["A"], gicko.get_glyph("a"))

        pixoo.clear()
        pixoo.draw_text("BDF Text", (0, 10), (255, 255, 255), tiny5)
        pixoo.draw_text("lowercase gicko", (0, 30), (255, 0, 0), gicko)


if __name__ == '__main__':
    unittest.main()

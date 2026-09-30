import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from custom_components.divoom_pixoo.pixoo64._bdf import FontManager, BdfFont
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
        with patch.object(Pixoo, "_Pixoo__load_counter"):
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
        self.assertTrue(any(self.pixoo._Pixoo__buffer))

    def test_default_font_does_not_depend_on_lookup_order(self):
        default = self.fm.get_font("")
        self.assertIsInstance(default, BdfFont)
        self.assertIs(default, self.fm.get_font("PICO_8"))
        self.assertIs(default, self.fm.get_font("unknown"))

    def test_all_bundled_fonts_render_unicode(self):
        for name in ["PICO_8", "Tiny5", "Tiny5Duo", "PixelifySans", "PressStart2P"]:
            with self.subTest(font=name):
                font = self.fm.get_font(name, fallback=False)
                self.assertIsInstance(font, BdfFont)
                self.pixoo.clear()
                self.pixoo.draw_text("Aäé→", (0, 8), (255, 255, 255), font)
                self.assertTrue(any(self.pixoo._Pixoo__buffer))

    def test_invalid_custom_font_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "broken.bdf").write_text(
                "STARTFONT 2.1\nSTARTCHAR A\nENCODING 65\n"
                "BBX 1 1 0 0\nBITMAP\nnot-hex\nENDCHAR\nENDFONT\n")
            self.fm.scan_directory(directory)
            with self.assertLogs(level="WARNING"):
                font = self.fm.get_font("broken")
            self.assertIs(font, self.fm.get_font("PICO_8"))


if __name__ == '__main__':
    unittest.main()

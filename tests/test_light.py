import unittest
from unittest.mock import Mock

from homeassistant.components.light import ColorMode
from homeassistant.config_entries import ConfigEntry

from custom_components.divoom_pixoo import DOMAIN, VERSION
from custom_components.divoom_pixoo.light import DivoomLight


class TestDivoomLight(unittest.TestCase):

    def setUp(self):
        test_config = ConfigEntry(entry_id='', domain='', title='', data='', options='', version=0, minor_version=0,
                                  source='')
        self.pixoo = Mock()
        self.light = DivoomLight(pixoo=self.pixoo, config_entry=test_config)

    def test_name(self):
        self.assertEqual("Light", self.light.name)

    def test_default_state(self):
        self.assertIsNone(self.light.is_on)

    def test_default_brightness(self):
        self.assertIsNone(self.light.brightness)

    def test_turn_on(self):
        self.light.turn_on()
        self.assertTrue(self.light.is_on)

    def test_turn_on_with_brightness(self):
        self.light.turn_on(brightness=37)
        self.assertTrue(self.light.is_on)
        self.assertEqual(37, self.light.brightness)

    def test_turn_off(self):
        self.light.turn_off()
        self.assertFalse(self.light.is_on)
        self.pixoo.set_screen.assert_called_once_with(False)

    def test_update(self):
        self.pixoo.get_state.return_value = True
        self.pixoo.get_brightness.return_value = 100

        self.light.update()

        self.pixoo.get_state.assert_called_once()
        self.pixoo.get_brightness.assert_called_once()
        self.assertTrue(self.light.is_on)
        self.assertEqual(255, self.light.brightness)

    def test_supported_color_modes(self):
        self.assertEqual(ColorMode.BRIGHTNESS, self.light.supported_color_modes.pop())

    def test_unique_id(self):
        self.assertTrue(self.light.unique_id.startswith("light_"))

    def test_device_info(self):
        device_info = self.light.device_info
        identifiers = device_info["identifiers"].pop()
        self.assertEqual(DOMAIN, identifiers[0])
        self.assertRegex(identifiers[1], r'^[a-zA-Z0-9]{32}$')
        self.assertEqual("", device_info["name"])
        self.assertEqual("Divoom", device_info['manufacturer'])
        self.assertEqual("Pixoo", device_info['model'])
        self.assertEqual(VERSION, device_info['sw_version'])



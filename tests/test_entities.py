import unittest

from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.config_entries import ConfigEntry

from custom_components.divoom_pixoo import Pixoo
from custom_components.divoom_pixoo.light import DivoomLight


class DummyPixoo(Pixoo):

    def __init__(self):
        self.calls = []
        self.args = []

    def set_screen(self, arg):
        self.calls.append('set_screen')
        self.args.append(arg)

    def received(self, message, arg=None):
        received_index = self.calls.index(message)
        if arg is None:
            return received_index > -1
        arg_val = self.args[received_index]
        return arg_val == arg




class TestDivoomLight(unittest.TestCase):

    def setUp(self):
        test_config = ConfigEntry(entry_id='', domain='', title='', data='', options='', version='', minor_version=0,
                                  source='')
        self.device = DummyPixoo()
        self.light = DivoomLight(pixoo=self.device, config_entry=test_config)

    def test_name(self):
        self.assertEqual("Light", self.light.name)

    def test_default_state(self):
        self.assertIsNone(self.light.is_on)

    def test_default_brightness(self):
        self.assertIsNone(self.light.brightness)

    def test_unique_id(self):
        self.assertTrue(self.light.unique_id.startswith("light_"))

    def test_device_info(self):
        device_info = self.light.device_info
        self.assertEqual("Divoom", device_info['manufacturer'])
        self.assertEqual("Pixoo", device_info['model'])

    def test_turn_on(self):
        self.light.turn_on()
        self.assertTrue(self.light.is_on)

    def test_turn_on_with_brightness(self):
        self.light.turn_on(brightness=37)
        self.assertTrue(self.light.is_on)
        self.assertEqual(37, self.light.brightness)

    def test_turn_off(self): #TODO: don't call it device, that's a loaded term in HA
        self.light.turn_off()
        self.assertFalse(self.light.is_on)
        self.assertTrue(self.device.received('set_screen', False))

    def test_update(self):
        # TODO: updates the entity from the pixoo
        self.assertTrue(False)

        # TODO  # class TestSensor(unittest.TestCase):  #     def test_name(self):  #         def test_device_info(self):

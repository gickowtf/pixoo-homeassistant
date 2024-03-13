import unittest

import requests_mock

from custom_components.divoom_pixoo.pixoo64._pixoo import Pixoo
from tests import IP_ADDRESS


@requests_mock.Mocker()
class TestPixoo(unittest.TestCase):
    def test_default_values(self, m):
        fake_response = {"error_code": 0, "PicId": 0}
        m.post('/post', json=fake_response)

        self.pixoo = Pixoo(IP_ADDRESS)

        # Confirm Pixoo object is created
        self.assertIsNotNone(self.pixoo)

        # Confirm defaults
        self.assertTrue(self.pixoo.refresh_connection_automatically)
        self.assertEqual(IP_ADDRESS, self.pixoo.address)
        self.assertFalse(self.pixoo.debug)
        self.assertEqual(64, self.pixoo.size)


if __name__ == '__main__':
    unittest.main()

import unittest

import requests
import requests_mock

from custom_components.divoom_pixoo.pixoo64._pixoo import Pixoo
from tests import IP_ADDRESS


@requests_mock.Mocker()
class TestPixoo(unittest.TestCase):
    primary_url = f"http://{IP_ADDRESS}/post"
    fallback_url = f"http://{IP_ADDRESS}:9000/divoom_api"

    def test_default_values(self, m):
        fake_response = {"error_code": 0, "PicId": 0}
        m.post(self.primary_url, json=fake_response)

        self.pixoo = Pixoo(IP_ADDRESS)

        # Confirm Pixoo object is created
        self.assertIsNotNone(self.pixoo)

        # Confirm defaults
        self.assertTrue(self.pixoo.refresh_connection_automatically)
        self.assertEqual(IP_ADDRESS, self.pixoo.address)
        self.assertFalse(self.pixoo.debug)
        self.assertEqual(64, self.pixoo.size)

    def test_uses_primary_endpoint_when_available(self, m):
        fake_response = {"error_code": 0, "PicId": 0}
        m.post(self.primary_url, json=fake_response)

        pixoo = Pixoo(IP_ADDRESS)
        pixoo.set_brightness(42)

        self.assertEqual(self.primary_url, pixoo._Pixoo__url)
        self.assertEqual(
            [self.primary_url, self.primary_url],
            [request.url for request in m.request_history]
        )
        self.assertEqual(
            {'Command': 'Channel/SetBrightness', 'Brightness': 42},
            m.request_history[-1].json()
        )

    def test_falls_back_to_divoom_api_when_primary_connection_fails(self, m):
        fake_response = {"error_code": 0, "PicId": 0}
        m.post(self.primary_url, exc=requests.exceptions.ConnectTimeout)
        m.post(self.fallback_url, json=fake_response)

        with self.assertLogs("custom_components.divoom_pixoo.pixoo64._pixoo", level="INFO") as logs:
            pixoo = Pixoo(IP_ADDRESS)
            pixoo.set_brightness(42)

        self.assertEqual(self.fallback_url, pixoo._Pixoo__url)
        self.assertEqual(
            [self.primary_url, self.fallback_url, self.fallback_url],
            [request.url for request in m.request_history]
        )
        self.assertEqual(
            {'Command': 'Channel/SetBrightness', 'Brightness': 42},
            m.request_history[-1].json()
        )
        self.assertTrue(
            any(f"Selected Pixoo API endpoint {self.fallback_url}" in message for message in logs.output)
        )


if __name__ == '__main__':
    unittest.main()

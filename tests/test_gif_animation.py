import asyncio
import base64
import json
import time
import unittest
from io import BytesIO
from unittest import mock

import requests_mock
from PIL import Image

from custom_components.divoom_pixoo.pixoo64._gif import (
    MAX_ANIMATION_FRAMES,
    clamp_pic_speed,
    extract_frames,
)
from custom_components.divoom_pixoo.pixoo64 import _pixoo as _pixoo_mod
from custom_components.divoom_pixoo.pixoo64._pixoo import Pixoo
IP_ADDRESS = "FAKE_IP_ADDRESS"


def make_gif(colors, size=(8, 8), durations=None):
    frames = [Image.new("RGB", size, color) for color in colors]
    buf = BytesIO()
    save_kwargs = {"format": "GIF", "save_all": True, "append_images": frames[1:],
                   "loop": 0}
    if durations is not None:
        save_kwargs["duration"] = durations
    frames[0].save(buf, **save_kwargs)
    buf.seek(0)
    return Image.open(buf)


def posted_commands(m):
    return [json.loads(req.text) for req in m.request_history
            if req.url.endswith("/post")]


@requests_mock.Mocker()
class TestPushAnimation(unittest.TestCase):
    def make_pixoo(self, m):
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()  # drop the GetHttpGifId handshake from __init__
        return pixoo

    def test_multi_frame_push_resets_then_sends_offsets(self, m):
        m.post("/post", json={"error_code": 0, "PicId": 0})
        pixoo = self.make_pixoo(m)

        frames = [pixoo.get_buffer(), pixoo.get_buffer(), pixoo.get_buffer()]
        pixoo.push_animation(frames, pic_speed=200)

        commands = posted_commands(m)
        self.assertEqual(1 + 3, len(commands))
        self.assertEqual("Draw/ResetHttpGifId", commands[0]["Command"])
        pic_ids = set()
        for offset, cmd in enumerate(commands[1:]):
            self.assertEqual("Draw/SendHttpGif", cmd["Command"])
            self.assertEqual(3, cmd["PicNum"])
            self.assertEqual(offset, cmd["PicOffset"])
            self.assertEqual(200, cmd["PicSpeed"])
            self.assertEqual(64, cmd["PicWidth"])
            pic_ids.add(cmd["PicID"])
            raw = base64.b64decode(cmd["PicData"])
            self.assertEqual(64 * 64 * 3, len(raw))
        self.assertEqual(1, len(pic_ids))  # shared PicID across frames

    def test_single_frame_push_keeps_static_path(self, m):
        m.post("/post", json={"error_code": 0, "PicId": 0})
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        pixoo.push_animation([pixoo.get_buffer()])

        commands = posted_commands(m)
        self.assertEqual(1, len(commands))
        self.assertEqual("Draw/SendHttpGif", commands[0]["Command"])
        self.assertEqual(1, commands[0]["PicNum"])
        self.assertEqual(1000, commands[0]["PicSpeed"])

    def test_push_after_animation_uses_fresh_pic_id(self, m):
        m.post("/post", json={"error_code": 0, "PicId": 0})
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        pixoo.push_animation([pixoo.get_buffer(), pixoo.get_buffer()])
        animated_ids = {cmd["PicID"] for cmd in posted_commands(m)[1:]}
        m.reset_mock()

        pixoo.push()
        static = posted_commands(m)[0]
        self.assertNotIn(static["PicID"], animated_ids)

    def test_empty_frames_push_nothing(self, m):
        m.post("/post", json={"error_code": 0, "PicId": 0})
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        pixoo.push_animation([])
        self.assertEqual([], posted_commands(m))

    def test_connection_reset_retries_frame(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"json": {"error_code": 0}},  # ResetHttpGifId
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"json": {"error_code": 0}},  # retry succeeds
            {"json": {"error_code": 0}},  # frame 2
        ])
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        with self.assertNoLogs(level="WARNING"):
            pixoo.push_animation([pixoo.get_buffer(), pixoo.get_buffer()])

        commands = posted_commands(m)
        frames = [cmd for cmd in commands if cmd["Command"] == "Draw/SendHttpGif"]
        self.assertEqual(3, len(frames))  # failed frame + retry + frame 2
        self.assertEqual([0, 0, 1], [cmd["PicOffset"] for cmd in frames])

    def test_push_animation_paces_frames(self, m):
        m.post("/post", json={"error_code": 0, "PicId": 0})
        pixoo = Pixoo(IP_ADDRESS)
        pixoo.frame_pause = 0.15
        m.reset_mock()

        with mock.patch.object(_pixoo_mod.time, "sleep") as sleep:
            pixoo.push_animation([pixoo.get_buffer(), pixoo.get_buffer(), pixoo.get_buffer()])
        self.assertEqual([mock.call(0.15), mock.call(0.15)], sleep.call_args_list)

    def test_refused_reset_falls_back_to_static(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"json": {"error_code": 1}},  # ResetHttpGifId refused
            {"json": {"error_code": 0}},  # static first-frame push
        ])
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        with self.assertLogs(level="WARNING"):
            pixoo.push_animation([pixoo.get_buffer(), pixoo.get_buffer()])

        commands = posted_commands(m)
        self.assertEqual(["Draw/ResetHttpGifId", "Draw/SendHttpGif"],
                         [cmd["Command"] for cmd in commands])
        # The fallback is the static path: one frame, default speed.
        self.assertEqual(1, commands[1]["PicNum"])
        self.assertEqual(1000, commands[1]["PicSpeed"])

    def test_raising_reset_falls_back_to_static(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"json": {"error_code": 0}},  # static first-frame push
        ])
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        with self.assertLogs(level="WARNING"):
            pixoo.push_animation([pixoo.get_buffer(), pixoo.get_buffer()])

        commands = posted_commands(m)
        self.assertEqual(["Draw/ResetHttpGifId", "Draw/SendHttpGif"],
                         [cmd["Command"] for cmd in commands])
        self.assertEqual(1, commands[1]["PicNum"])

    def test_raising_reset_keeps_the_static_push_contract(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
        ])
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        # The reset fallback goes through push(), which still raises when the
        # device is unreachable: the sensor's error handling depends on it.
        with self.assertRaises(ConnectionResetError):
            pixoo.push_animation([pixoo.get_buffer(), pixoo.get_buffer()])

    def test_zero_frames_sent_keeps_previous_page(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"json": {"error_code": 0}},  # ResetHttpGifId
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"json": {"error_code": 0}},  # static fallback push
        ])
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        with self.assertLogs(level="WARNING"):
            pixoo.push_animation([pixoo.get_buffer(), pixoo.get_buffer()])

        commands = posted_commands(m)
        kinds = [(cmd["Command"], cmd.get("PicNum")) for cmd in commands]
        self.assertIn(("Draw/ResetHttpGifId", None), kinds)
        # Frame 0 failed twice: zero frames sent, no partial-animation
        # fallback; the next scheduled page draw recovers.
        self.assertEqual(1, len([k for k in kinds if k[0] == "Draw/ResetHttpGifId"]))
        self.assertEqual([], [k for k in kinds if k == ("Draw/SendHttpGif", 1)])

    def test_partial_failure_falls_back_to_static(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"json": {"error_code": 0}},  # ResetHttpGifId
            {"json": {"error_code": 0}},  # frame 0 ok
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"json": {"error_code": 0}},  # static fallback push
        ])
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        with self.assertLogs(level="WARNING"):
            pixoo.push_animation([pixoo.get_buffer(), pixoo.get_buffer()])

        commands = posted_commands(m)
        kinds = [(cmd["Command"], cmd.get("PicNum")) for cmd in commands]
        # Partial animation (1/2) re-pushes the first frame as a static page.
        self.assertEqual(("Draw/SendHttpGif", 1), kinds[-1])


@requests_mock.Mocker()
class TestStaticPushErrors(unittest.TestCase):
    """``push()`` keeps the exception contract it had before the helper.

    It used to post the frame itself, so a transport failure propagated to the
    caller and the sensor's render error handling. Sharing
    ``__send_gif_frame`` with the animation path may not turn that into a
    swallowed False.
    """

    def make_pixoo(self, m):
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()  # drop the GetHttpGifId handshake from __init__
        return pixoo

    def test_static_push_raises_after_one_retry(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
        ])
        pixoo = self.make_pixoo(m)

        with self.assertRaises(ConnectionResetError):
            pixoo.push()

        sends = [c for c in posted_commands(m) if c["Command"] == "Draw/SendHttpGif"]
        self.assertEqual(2, len(sends))  # one retry, then the raise

    def test_static_push_raises_on_a_bad_response(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"text": "not json"},
        ])
        pixoo = self.make_pixoo(m)

        with self.assertRaises(ValueError):
            pixoo.push()


class TestExtractFrames(unittest.TestCase):

    def test_static_image_yields_one_frame(self):
        img = Image.new("RGB", (8, 8), (255, 0, 0))
        frames, speed = extract_frames(img)
        self.assertEqual(1, len(frames))
        self.assertEqual(200, speed)

    def test_unsized_static_frame_survives_source_close(self):
        img = Image.new("RGB", (8, 8), (255, 0, 0))
        frames, _ = extract_frames(img)
        img.close()  # sensor closes the source after decode; frame must live on
        self.assertEqual((255, 0, 0), frames[0].convert("RGB").getpixel((0, 0)))

    def test_animated_gif_yields_all_frames_with_mean_delay(self):
        img = make_gif([(255, 0, 0), (0, 255, 0), (0, 0, 255)],
                       durations=[100, 200, 400])
        frames, speed = extract_frames(img)
        self.assertEqual(3, len(frames))
        self.assertEqual(233, speed)  # mean of 100/200/400, not the 200 default

    def test_speed_override_wins_and_clamps(self):
        img = make_gif([(255, 0, 0), (0, 255, 0)], durations=[100, 100])
        _, speed = extract_frames(img, speed_override=5)
        self.assertEqual(50, speed)  # clamped to floor
        _, speed = extract_frames(img, speed_override=99999)
        self.assertEqual(2000, speed)  # clamped to ceiling

    def test_frame_cap(self):
        img = make_gif([(i % 256, 0, 0) for i in range(MAX_ANIMATION_FRAMES + 5)])
        frames, _ = extract_frames(img)
        self.assertEqual(MAX_ANIMATION_FRAMES, len(frames))

    def test_resize_applies_to_every_frame(self):
        img = make_gif([(255, 0, 0), (0, 255, 0)], size=(16, 16))
        frames, _ = extract_frames(img, width=8, height=8)
        self.assertEqual(2, len(frames))
        for frame in frames:
            self.assertEqual((8, 8), frame.size)

    def test_clamp_pic_speed_rejects_garbage(self):
        self.assertEqual(200, clamp_pic_speed(None))
        self.assertEqual(200, clamp_pic_speed("fast"))
        self.assertEqual(50, clamp_pic_speed(-10))
        self.assertEqual(2000, clamp_pic_speed(10**9))


class CountingTemplate:
    """Stand-in for ``Template`` whose value changes on every render."""

    renders = 0

    def __init__(self, value, hass):
        self._value = value

    def async_render(self, variables=None):
        type(self).renders += 1
        return str(type(self).renders)


class TestFrameStableTemplates(unittest.TestCase):
    """One page render renders a template once, not once per frame.

    A page is composited once per frame, so a template evaluated per frame can
    change value *inside* one page: a render that straddles a minute boundary
    bakes two clock values into the same animation, which the panel then shows
    alternating.
    """

    def setUp(self):
        import custom_components.divoom_pixoo.sensor as sensor_mod
        self.sensor_mod = sensor_mod
        CountingTemplate.renders = 0
        self.pixoo = mock.Mock()
        self.pixoo.size = 8
        config_entry = mock.Mock()
        config_entry.options = {"pages_data": [], "scan_interval": 15}
        self.entity = sensor_mod.Pixoo64(pixoo=self.pixoo, config_entry=config_entry)
        self.entity.hass = mock.Mock()

    def render(self, components, frame_count=3):
        frames = [Image.new("RGB", (8, 8), (index, 0, 0))
                  for index in range(frame_count)]
        with mock.patch.object(self.sensor_mod, "Template", CountingTemplate), \
             mock.patch.object(self.entity, "_load_image_frames",
                               return_value=(frames, 200, Image.BOX)):
            self.entity._render_components(self.pixoo, components, {})

    def test_text_template_renders_once_per_page_render(self):
        components = [
            {"type": "text", "content": "{{ now().strftime('%H:%M') }}",
             "position": [0, 0], "color": "white"},
            {"type": "image", "position": [0, 0]},
        ]
        self.render(components)

        drawn = [call.args[0] for call in self.pixoo.draw_text.call_args_list]
        self.assertEqual(3, len(drawn))  # one draw per frame
        self.assertEqual(1, len(set(drawn)))  # all frames show the same value

    def test_rectangle_template_renders_once_per_page_render(self):
        components = [
            {"type": "rectangle", "position": [0, 0], "size": [8, 8]},
            {"type": "image", "position": [0, 0]},
        ]
        self.render(components)

        rectangles = [call.args
                      for call in self.pixoo.draw_filled_rectangle.call_args_list]
        self.assertEqual(3, len(rectangles))  # one draw per frame
        self.assertEqual(1, len(set(map(str, rectangles))))  # same geometry

    def test_each_render_renders_the_templates_again(self):
        components = [{"type": "text", "content": "{{ now() }}",
                       "position": [0, 0]}]
        self.render(components, frame_count=1)
        first = self.pixoo.draw_text.call_args_list[0].args[0]
        self.render(components, frame_count=1)
        second = self.pixoo.draw_text.call_args_list[-1].args[0]
        self.assertNotEqual(first, second)  # the cache is per render, not forever


class _ThreadPoolHass:
    """Stand-in for the hass object that really runs executor jobs off-thread."""

    @staticmethod
    async def async_add_executor_job(func, *args):
        return await asyncio.get_running_loop().run_in_executor(None, func, *args)


class TestRenderSerialization(unittest.IsolatedAsyncioTestCase):
    """Renders on one entity never overlap on the shared Pixoo.

    The next page is scheduled before the current render is awaited, and the
    page services render too, so without a lock a short page duration (or a
    slow push) starts a second render on the same buffer, PicID counter and
    HTTP connection.
    """

    def setUp(self):
        import custom_components.divoom_pixoo.sensor as sensor_mod
        self.sensor_mod = sensor_mod
        self.pixoo = mock.Mock()
        self.pixoo.size = 8
        self.pixoo.address = "FAKE_IP_ADDRESS"
        config_entry = mock.Mock()
        config_entry.options = {"pages_data": [], "scan_interval": 15}
        self.entity = sensor_mod.Pixoo64(pixoo=self.pixoo, config_entry=config_entry)
        self.entity.hass = _ThreadPoolHass()
        self.active = 0
        self.peak = 0
        self.rendered = []

    def render(self, page):
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.rendered.append(page)
        time.sleep(0.05)  # hold the "device" long enough to overlap
        self.active -= 1

    async def test_overlapping_render_calls_do_not_interleave(self):
        self.entity._render_page = self.render

        await asyncio.gather(
            self.entity._async_render_page({"page_type": "clock", "id": 1}),
            self.entity._async_render_page({"page_type": "clock", "id": 2}),
        )

        self.assertEqual(2, len(self.rendered))  # both renders still happen
        self.assertEqual(1, self.peak)  # but never at the same time

    async def test_page_services_render_through_the_lock(self):
        calls = []

        async def fake_render(page):
            calls.append(page)

        self.entity._async_render_page = fake_render
        page = {"page_type": "clock", "id": 3}
        self.entity.page = page

        await self.entity.async_show_message(page, duration=5)
        await self.entity.update_page()

        self.assertEqual([page, page], calls)


if __name__ == "__main__":
    unittest.main()

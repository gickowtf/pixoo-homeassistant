import asyncio
import base64
import json
import tempfile
import time
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

import requests_mock
from PIL import Image, ImageChops
from homeassistant.core import CoreState

from custom_components.divoom_pixoo.pixoo64._gif import (
    MAX_ANIMATION_FRAMES,
    clamp_pic_speed,
    encode_page_gif,
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


    def test_pixel_push_trims_to_the_frame_cap(self, m):
        # The push is where the cap belongs: frames past it are dropped, with
        # the warning that used to come from the decoder.
        m.post("/post", json={"error_code": 0, "PicId": 0})
        pixoo = self.make_pixoo(m)

        frames = [pixoo.get_buffer() for _ in range(MAX_ANIMATION_FRAMES + 5)]
        pixoo.push_animation(frames, pic_speed=200)

        sends = [c for c in posted_commands(m) if c["Command"] == "Draw/SendHttpGif"]
        self.assertEqual(MAX_ANIMATION_FRAMES, len(sends))
        self.assertEqual(MAX_ANIMATION_FRAMES, sends[0]["PicNum"])


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


@requests_mock.Mocker()
class TestPlayGif(unittest.TestCase):
    def make_pixoo(self, m):
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()  # drop the GetHttpGifId handshake from __init__
        return pixoo

    def test_play_gif_returns_true_on_ack(self, m):
        m.post("/post", json={"error_code": 0, "PicId": 0})
        pixoo = self.make_pixoo(m)

        self.assertTrue(pixoo.play_gif("http://ha:8123/api/divoom_pixoo/entry/page.gif"))
        commands = posted_commands(m)
        self.assertEqual(1, len(commands))
        self.assertEqual("Device/PlayTFGif", commands[0]["Command"])
        self.assertEqual(2, commands[0]["FileType"])

    def test_play_gif_returns_false_on_error_code(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"json": {"error_code": 7}},
        ])
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        self.assertFalse(pixoo.play_gif("http://ha:8123/api/divoom_pixoo/entry/page.gif"))

    def test_play_gif_returns_false_on_transport_error(self, m):
        m.post("/post", [
            {"json": {"error_code": 0, "PicId": 0}},  # __init__ handshake
            {"exc": ConnectionResetError(104, "Connection reset by peer")},
        ])
        pixoo = Pixoo(IP_ADDRESS)
        m.reset_mock()

        self.assertFalse(pixoo.play_gif("http://ha:8123/api/divoom_pixoo/entry/page.gif"))

class TestEncodePageGif(unittest.TestCase):
    """The encoder contract: one opaque delta GIF per page.

    Full-canvas first frame, later frames cropped to what changed, disposal 1
    everywhere, **no transparency flag anywhere**, one global colour table,
    one delay for every frame, loop forever, returned as bytes.
    """

    def make_frames(self, size, colors):
        return [[c for pixel in [color] * (size * size) for c in pixel]
                for color in colors]

    @staticmethod
    def walk(blob):
        """Return (graphic controls, image descriptors) from a GIF blob.

        Each graphic control is ``(disposal, transparency_flag, delay_cs)``,
        each descriptor ``(left, top, width, height, has_local_table)``.
        """
        if blob[:6] not in (b"GIF87a", b"GIF89a"):
            raise AssertionError("not a GIF")
        position = 13 + 3 * 2 ** ((blob[10] & 0x07) + 1)
        controls, descriptors = [], []
        while position < len(blob):
            block = blob[position]
            if block == 0x21:
                if blob[position + 1] == 0xF9 and blob[position + 2] == 4:
                    packed = blob[position + 3]
                    controls.append(((packed >> 2) & 0x07, bool(packed & 0x01),
                                     blob[position + 4] | blob[position + 5] << 8))
                cursor = position + 2
                while blob[cursor] != 0:
                    cursor += 1 + blob[cursor]
                position = cursor + 1
            elif block == 0x2C:
                flags = blob[position + 9]
                descriptors.append((
                    blob[position + 1] | blob[position + 2] << 8,
                    blob[position + 3] | blob[position + 4] << 8,
                    blob[position + 5] | blob[position + 6] << 8,
                    blob[position + 7] | blob[position + 8] << 8,
                    bool(flags & 0x80)))
                cursor = position + 11 + (3 * 2 ** ((flags & 0x07) + 1)
                                          if flags & 0x80 else 0)
                while blob[cursor] != 0:
                    cursor += 1 + blob[cursor]
                position = cursor + 1
            elif block == 0x3B:
                break
            else:
                raise AssertionError(f"unexpected GIF block 0x{block:02x}")
        return controls, descriptors

    def test_every_frame_is_disposal_1_and_never_transparent(self):
        size = 8
        frames = self.make_frames(size, [(0, 0, 0), (255, 0, 0), (0, 255, 0)])
        blob, digest = encode_page_gif(frames, size, 200)
        self.assertEqual(8, len(digest))
        controls, descriptors = self.walk(blob)
        self.assertTrue(blob[10] & 0x80)  # one global table
        self.assertEqual(len(frames), len(controls))
        self.assertEqual([1] * len(frames), [c[0] for c in controls])
        self.assertEqual([False] * len(frames), [c[1] for c in controls])
        self.assertEqual([20] * len(frames), [c[2] for c in controls])
        self.assertEqual([False] * len(frames), [d[4] for d in descriptors])
        with Image.open(BytesIO(blob)) as gif:
            self.assertNotIn("transparency", gif.info)
            for index in range(len(frames)):
                gif.seek(index)
                self.assertEqual(1, gif.disposal_method)

    def test_first_frame_is_full_canvas_and_the_rest_are_crops(self):
        size = 16
        images = []
        for step in range(4):
            image = Image.new("RGB", (size, size), (0, 0, 0))
            for y in range(4, 8):
                for x in range(2 + step, 6 + step):
                    image.putpixel((x, y), (255, 200, 0))
            images.append(image)
        blob, _ = encode_page_gif([list(i.tobytes()) for i in images], size, 200)
        _, descriptors = self.walk(blob)
        self.assertEqual((0, 0, size, size), descriptors[0][:4])
        for index in range(1, len(images)):
            # the crop is exactly what changed since the previous frame
            box = ImageChops.difference(images[index],
                                        images[index - 1]).getbbox()
            self.assertEqual(
                (box[0], box[1], box[2] - box[0], box[3] - box[1]),
                descriptors[index][:4])
            self.assertLess(descriptors[index][2], size)

    def test_the_file_loops_forever(self):
        size = 8
        frames = self.make_frames(size, [(0, 0, 0), (255, 0, 0), (0, 0, 255)])
        blob, _ = encode_page_gif(frames, size, 200)
        table_end = 13 + 3 * 2 ** ((blob[10] & 0x07) + 1)
        # the loop extension sits right after the global colour table
        self.assertEqual(b"\x21\xff\x0bNETSCAPE2.0",
                         blob[table_end:table_end + 14])
        with Image.open(BytesIO(blob)) as gif:
            self.assertEqual(0, gif.info.get("loop"))

    def test_roundtrip_is_pixel_exact_for_a_sixty_frame_page(self):
        """A page whose colours fit one palette must survive the trip exactly.

        60 frames is also the length the pixel push cannot carry (it caps out
        around 30), so this is the case the hosted path exists for.
        """
        size = 16
        frames = []
        for index in range(60):
            image = Image.new("RGB", (size, size), (10, 20, 30))
            for y in range(size):
                for x in range(size):
                    if (x + index) % 8 < 2:
                        image.putpixel((x, y), (200, 40, 90))
            frames.append(list(image.tobytes()))
        blob, _ = encode_page_gif(frames, size, 200)
        with Image.open(BytesIO(blob)) as gif:
            self.assertEqual(60, gif.n_frames)
            self.assertEqual(200, gif.info.get("duration"))
            for index in range(60):
                gif.seek(index)
                self.assertEqual(bytes(frames[index]),
                                 gif.convert("RGB").tobytes())

    def test_a_richer_page_is_quantised_to_one_palette_not_rejected(self):
        size = 16
        frames = []
        for index in range(3):
            image = Image.new("RGB", (size, size))
            for y in range(size):
                for x in range(size):
                    image.putpixel((x, y), ((x * 5 + index) % 256,
                                            (y * 7 + index) % 256,
                                            (x * y + index) % 256))
            frames.append(list(image.tobytes()))
        source_colours = len({pixel for frame in frames
                              for pixel in zip(frame[0::3], frame[1::3],
                                               frame[2::3])})
        self.assertGreater(source_colours, 256,
                           "the quantised branch is only exercised above 256")
        blob, _ = encode_page_gif(frames, size, 200)
        controls, descriptors = self.walk(blob)
        self.assertTrue(blob[10] & 0x80)  # one global table
        self.assertEqual(len(frames), len(controls))
        self.assertEqual([1] * len(frames), [c[0] for c in controls])
        self.assertEqual([False] * len(frames), [c[1] for c in controls])
        self.assertEqual([False] * len(descriptors),
                         [d[4] for d in descriptors])  # no local tables
        with Image.open(BytesIO(blob)) as gif:
            gif.seek(0)
            self.assertLessEqual(
                len(gif.convert("RGB").getcolors(maxcolors=1 << 16)), 256)

    def test_a_richer_page_decodes_visible_not_black(self):
        """The quantised branch's global table must carry the real colours.

        Regression: the table was serialised from Pillow's *flat*
        ``getpalette()`` list as if it held triples, so every >256-colour page
        encoded with an all-black global table - a real page rendered as a
        black screen on the panel, and the weaker assertion above (at most 256
        colours) passed anyway, because black is one colour.
        """
        size = 64
        frames = []
        for index in range(3):
            image = Image.new("RGB", (size, size))
            for y in range(size):
                for x in range(size):
                    image.putpixel((x, y), ((x * 4 + index) % 256,
                                            (y * 4) % 256,
                                            (x * y + index) % 256))
            frames.append(list(image.tobytes()))
        source_colours = len({pixel for frame in frames
                              for pixel in zip(frame[0::3], frame[1::3],
                                               frame[2::3])})
        self.assertGreater(source_colours, 256)
        blob, _ = encode_page_gif(frames, size, 200)
        with Image.open(BytesIO(blob)) as gif:
            self.assertEqual(len(frames), gif.n_frames)
            for index in range(gif.n_frames):
                gif.seek(index)
                decoded = gif.convert("RGB")
                extrema = decoded.getextrema()
                self.assertGreater(max(high for _, high in extrema), 100,
                                   f"frame {index} decoded black")
                error = sum(abs(a - b) for a, b in
                            zip(decoded.tobytes(), frames[index])) / len(frames[index])
                self.assertLess(error, 20.0,
                                f"frame {index} is not a sane quantisation")

    def test_palette_bytes_takes_a_flat_palette_and_pads_to_768(self):
        from custom_components.divoom_pixoo.pixoo64._gif import _palette_bytes
        flat = [255, 0, 0, 0, 255, 0]
        self.assertEqual(bytes(flat), _palette_bytes(flat)[:6])
        self.assertEqual(768, len(_palette_bytes(flat)))
        self.assertEqual(bytes([7] * 768), _palette_bytes([7] * 900))

    def test_duplicate_frame_merges_into_the_previous_delay(self):
        """An identical frame carries its duration instead of its pixels.

        Pillow's writer coalesces these the same way, and animated art really
        contains them, but the encoder decides it itself: the file holds one
        frame with the summed delay. The digest still covers every input frame,
        because it means "the composite is on the panel", not "the file has
        these bytes".
        """
        size = 8
        black, red = (0, 0, 0), (255, 0, 0)
        frames = self.make_frames(size, [black, red, red, black])
        blob, digest = encode_page_gif(frames, size, 200)
        controls, _ = self.walk(blob)
        self.assertEqual([20, 40, 20], [c[2] for c in controls])
        with Image.open(BytesIO(blob)) as gif:
            self.assertEqual(3, gif.n_frames)
            gif.seek(2)
            self.assertEqual(bytes(frames[3]), gif.convert("RGB").tobytes())
        unique = self.make_frames(size, [black, red, black])
        _, other = encode_page_gif(unique, size, 200)
        self.assertNotEqual(digest, other)

    def test_encode_partial_content_decodes_exact(self):
        # Small moving block on a black page: the decoder must reproduce the
        # page exactly without relying on a clear-to-background between frames
        # (disposal 1 leaves the canvas in place).
        size = 16
        bufs = []
        for i in range(4):
            img = Image.new("RGB", (size, size))
            for y in range(2, 6):
                for x in range(i, i + 4):
                    img.putpixel((x, y), (255, 200, 0))
            bufs.append(list(img.tobytes()))
            self.assertEqual(size * size * 3, len(bufs[-1]))
        blob, _ = encode_page_gif(bufs, size, 130)
        with Image.open(BytesIO(blob)) as gif:
            self.assertEqual(4, getattr(gif, "n_frames", 1))
            for index in range(4):
                gif.seek(index)
                self.assertEqual(1, gif.disposal_method)
                self.assertEqual(bytes(bufs[index]),
                                 gif.convert("RGB").tobytes())

    def test_rejects_empty_and_missized_frames(self):
        size = 8
        with self.assertRaises(ValueError):
            encode_page_gif([], size, 200)
        with self.assertRaises(ValueError):
            encode_page_gif([[0, 0, 0]], size, 200)


class TestHostedAnimationRouting(unittest.TestCase):
    """A multi-frame page is played from a file; everything else is pixels."""

    BASE_URL = "http://192.168.1.190:8123"
    ENTRY_ID = "entry-1"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.config_dir = Path(tmp.name)

    def make_entity(self):
        import custom_components.divoom_pixoo.sensor as sensor_mod
        hass = mock.Mock()
        hass.state = CoreState.running
        # Like Config.path: everything is relative to the config dir.
        hass.config.path.side_effect = lambda *parts: str(self.config_dir.joinpath(*parts))
        pixoo = mock.Mock()
        pixoo.size = 8
        pixoo.play_gif.return_value = True
        config_entry = mock.Mock()
        config_entry.entry_id = self.ENTRY_ID
        config_entry.options = {"pages_data": [], "scan_interval": 15}
        entity = sensor_mod.Pixoo64(pixoo=pixoo, config_entry=config_entry)
        entity.hass = hass
        entity._current_page_index = 0
        return sensor_mod, entity, pixoo

    def play(self, sensor_mod, entity, pixoo, frames):
        """One hosted play; the URL and folder contract is covered elsewhere."""
        with mock.patch.object(sensor_mod, "get_url", return_value=self.BASE_URL):
            entity._play_hosted_animation(pixoo, frames, 200)

    def test_hosted_play_used_for_multi_frame(self):
        sensor_mod, entity, pixoo = self.make_entity()
        self.play(sensor_mod, entity, pixoo, [[255, 0, 0] * 64, [0, 255, 0] * 64])

        pixoo.play_gif.assert_called_once()
        self.assertEqual(
            f"{self.BASE_URL}/local/{sensor_mod.HOSTED_PAGES_DIRNAME}/"
            f"{entity._page_folder}/{sensor_mod.HOSTED_PAGE_FILENAME}",
            pixoo.play_gif.call_args[0][0])
        pixoo.push_animation.assert_not_called()
        # The bytes that URL serves are the page we just encoded.
        page = (self.config_dir / "www" / sensor_mod.HOSTED_PAGES_DIRNAME
                / entity._page_folder / sensor_mod.HOSTED_PAGE_FILENAME)
        self.assertTrue(page.read_bytes().startswith(b"GIF89a"))

    def test_fallback_to_push_on_play_failure(self):
        sensor_mod, entity, pixoo = self.make_entity()
        pixoo.play_gif.return_value = False
        self.play(sensor_mod, entity, pixoo, [[255, 0, 0] * 64, [0, 255, 0] * 64])
        pixoo.push_animation.assert_called_once()

    def test_fallback_to_push_on_https_base(self):
        sensor_mod, entity, pixoo = self.make_entity()
        with mock.patch.object(sensor_mod, "get_url",
                               return_value="https://home.example.com"):
            entity._play_hosted_animation(pixoo, [[255, 0, 0] * 64, [0, 255, 0] * 64], 200)
        pixoo.play_gif.assert_not_called()
        pixoo.push_animation.assert_called_once()
        # https never gets as far as writing a page
        self.assertFalse((self.config_dir / "www").exists())


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

    def test_returns_every_frame(self):
        # The decoder must hand over every frame: a hosted page is a URL the
        # panel fetches, so long loops have to survive decoding intact. The cap
        # lives on the pixel push (see test_pixel_push_trims_to_the_frame_cap).
        img = make_gif([(i % 256, 0, 0) for i in range(MAX_ANIMATION_FRAMES + 5)])
        frames, _ = extract_frames(img)
        self.assertEqual(MAX_ANIMATION_FRAMES + 5, len(frames))

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

"""Contract for the hosted-gif playback path (``sensor.py``).

The panel's ``Device/PlayTFGif`` **starts a player and never stops the
previous one**, so the only safe shape is: one play per changed composite, and
no play at all when the bytes did not change.

The page is a file under ``www/pixoo_pages/<entry prefix>-<random token>/``,
served without authentication, so the folder token is the page's only access
control: it is random per setup and it never reaches the log.
"""

import asyncio
import hashlib
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import custom_components.divoom_pixoo.sensor as sensor_mod
from custom_components.divoom_pixoo.const import DOMAIN
from custom_components.divoom_pixoo.sensor import (
    HOSTED_PAGES_DIRNAME,
    HOSTED_PAGE_FILENAME,
    entry_page_prefix,
    page_folder_name,
    remove_page_folders,
)
from homeassistant.core import CoreState

SIZE = 8
BASE_URL = "http://192.168.1.190:8123"
ENTRY_ID = "entry-1"
OTHER_ENTRY_ID = "entry-2"


def frame(color):
    return list(color) * (SIZE * SIZE)


RED = frame((255, 0, 0))
GREEN = frame((0, 255, 0))
BLUE = frame((0, 0, 255))


class HostedPageTest(unittest.TestCase):
    """Base: a real (temporary) ``www/`` and entities wired to it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.config_dir = Path(tmp.name)
        self.www = self.config_dir / "www"

    @property
    def pages_dir(self):
        return self.www / HOSTED_PAGES_DIRNAME

    def make_hass(self, state=CoreState.running):
        hass = mock.Mock()
        hass.state = state
        # Like Config.path: everything is relative to the config dir.
        hass.config.path.side_effect = lambda *parts: str(self.config_dir.joinpath(*parts))
        # Executor jobs run inline, so the blocking sweeps are observable.
        hass.async_add_executor_job = mock.AsyncMock(
            side_effect=lambda target, *args: target(*args))
        hass.data = {DOMAIN: {ENTRY_ID: {"pixoo": mock.Mock()},
                              OTHER_ENTRY_ID: {"pixoo": mock.Mock()}}}
        return hass

    def make_entity(self, entry_id=ENTRY_ID, state=CoreState.running, hass=None):
        pixoo = mock.Mock()
        pixoo.size = SIZE
        pixoo.play_gif.return_value = True
        config_entry = mock.Mock()
        config_entry.entry_id = entry_id
        config_entry.options = {"pages_data": [], "scan_interval": 15}
        entity = sensor_mod.Pixoo64(pixoo=pixoo, config_entry=config_entry)
        entity.hass = hass if hass is not None else self.make_hass(state)
        return entity, pixoo

    def play(self, entity, pixoo, frames):
        with mock.patch.object(sensor_mod, "get_url", return_value=BASE_URL):
            entity._play_hosted_animation(pixoo, frames, 200)

    def played_urls(self, pixoo):
        return [call.args[0] for call in pixoo.play_gif.call_args_list]

    def page_url(self, entity):
        return (f"{BASE_URL}/local/{HOSTED_PAGES_DIRNAME}/"
                f"{entity._page_folder}/{HOSTED_PAGE_FILENAME}")

    def page_files(self):
        return sorted(self.pages_dir.glob(f"*/{HOSTED_PAGE_FILENAME}"))

    def make_old_folder(self, entry_id, token="stale-token"):
        """A folder a previous run left behind, with a page in it."""
        folder = self.pages_dir / f"{entry_page_prefix(entry_id)}-{token}"
        folder.mkdir(parents=True)
        (folder / HOSTED_PAGE_FILENAME).write_bytes(b"old page")
        return folder


class TestFolderName(HostedPageTest):
    def test_name_is_the_entry_prefix_dash_a_fresh_token(self):
        name = page_folder_name(ENTRY_ID)
        prefix, _, token = name.partition("-")
        self.assertEqual(entry_page_prefix(ENTRY_ID), prefix)
        self.assertEqual(hashlib.sha256(ENTRY_ID.encode()).hexdigest()[:8], prefix)
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9_-]{16}", token), name)
        # fresh per setup: a stale folder can never be re-used, so the previous
        # URL dies at the restart instead of being silently revalidated
        self.assertNotEqual(name, page_folder_name(ENTRY_ID))

    def test_entries_get_different_prefixes(self):
        self.assertNotEqual(entry_page_prefix(ENTRY_ID),
                            entry_page_prefix(OTHER_ENTRY_ID))

    def test_the_url_the_panel_gets_stays_short(self):
        # The panel timed out on a ~300-char signed URL and never fetched it;
        # this shape is the one it has fetched all along (/local page.gif).
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        url = self.played_urls(pixoo)[0]
        self.assertEqual(self.page_url(entity), url)
        self.assertLess(len(url), 90, f"panel URL is {len(url)} chars: {url}")
        self.assertTrue(url.startswith(f"{BASE_URL}/local/{HOSTED_PAGES_DIRNAME}/"))
        self.assertTrue(url.endswith(f"/{HOSTED_PAGE_FILENAME}"))
        self.assertNotIn("authSig", url)


class TestFolderOwnership(HostedPageTest):
    def test_two_entries_never_share_a_folder(self):
        first, first_pixoo = self.make_entity(ENTRY_ID)
        second, second_pixoo = self.make_entity(OTHER_ENTRY_ID)
        self.play(first, first_pixoo, [RED, GREEN])
        self.play(second, second_pixoo, [BLUE, GREEN])

        self.assertNotEqual(first._page_folder, second._page_folder)
        self.assertNotEqual(first._page_prefix, second._page_prefix)
        pages = self.page_files()
        self.assertEqual(2, len(pages))
        self.assertEqual({first._page_folder, second._page_folder},
                         {page.parent.name for page in pages})

    def test_setup_sweeps_only_this_entrys_old_folders(self):
        mine = self.make_old_folder(ENTRY_ID)
        other = self.make_old_folder(OTHER_ENTRY_ID)
        older_layout = self.pages_dir / HOSTED_PAGE_FILENAME  # a plain file
        older_layout.write_bytes(b"old single-file page")
        unrelated = self.pages_dir / "notes"
        unrelated.mkdir()
        my_prefix_file = self.pages_dir / f"{entry_page_prefix(ENTRY_ID)}-file"
        my_prefix_file.write_bytes(b"not a folder")

        remove_page_folders(self.make_hass(), ENTRY_ID)

        self.assertFalse(mine.exists())
        self.assertTrue(other.exists(), "another device's page was removed")
        self.assertTrue(older_layout.exists())
        self.assertTrue(unrelated.exists())
        self.assertTrue(my_prefix_file.exists())

    def test_setup_entry_sweeps_its_own_stale_folders(self):
        stale = self.make_old_folder(ENTRY_ID)
        other = self.make_old_folder(OTHER_ENTRY_ID)
        hass = self.make_hass()
        added = []

        asyncio.run(sensor_mod.async_setup_entry(
            hass, self.make_entry(ENTRY_ID),
            lambda entities, update: added.extend(entities)))

        self.assertFalse(stale.exists())
        self.assertTrue(other.exists())
        self.assertEqual(1, len(added))
        # ...and the entity that came out of setup owns a different, fresh one.
        self.assertNotEqual(stale.name, added[0]._page_folder)

    def make_entry(self, entry_id):
        entry = mock.Mock(entry_id=entry_id)
        entry.options = {"pages_data": [], "scan_interval": 15}
        return entry

    def test_unload_removes_this_entrys_folders_and_none_others(self):
        other = self.make_old_folder(OTHER_ENTRY_ID)
        stale = self.make_old_folder(ENTRY_ID)
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        current = self.pages_dir / entity._page_folder
        self.assertTrue((current / HOSTED_PAGE_FILENAME).exists())

        asyncio.run(entity.async_will_remove_from_hass())

        self.assertFalse(current.exists())
        self.assertFalse(stale.exists())  # ours as well; none of them is reachable
        self.assertTrue(other.exists(), "another device's page was removed")

    def test_a_folder_is_only_written_after_a_play(self):
        entity, pixoo = self.make_entity()
        self.assertFalse(self.pages_dir.exists())
        self.play(entity, pixoo, [RED, GREEN])
        page = self.pages_dir / entity._page_folder / HOSTED_PAGE_FILENAME
        self.assertTrue(page.exists())
        self.assertTrue(page.read_bytes().startswith(b"GIF89a"))


class TestNotRunningYet(HostedPageTest):
    def test_pixels_until_home_assistant_is_running(self):
        # The first rotation tick can fire during platform setup, while HA's
        # HTTP server is not answering yet: the panel then times out on the
        # fetch and refuses connections for ~30 s. Note the gate is
        # CoreState.running and not hass.is_running, which is already True
        # while STARTING - the exact window that broke the panel.
        for state in (CoreState.not_running, CoreState.starting, CoreState.stopping):
            with self.subTest(state=state):
                entity, pixoo = self.make_entity(state=state)
                self.play(entity, pixoo, [RED, GREEN])

                pixoo.play_gif.assert_not_called()
                pixoo.push_animation.assert_called_once()
                self.assertIsNone(entity._last_hosted_digest)
                self.assertFalse(self.pages_dir.exists())


class TestDigestSkip(HostedPageTest):
    def test_unchanged_digest_does_not_play_again(self):
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(1, pixoo.play_gif.call_count)
        pixoo.push_animation.assert_not_called()

    def test_changed_digest_plays_again(self):
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        self.play(entity, pixoo, [RED, BLUE])
        self.assertEqual(2, pixoo.play_gif.call_count)
        self.assertEqual([self.page_url(entity)] * 2, self.played_urls(pixoo))

    def test_a_pixel_render_forgets_the_digest(self):
        # A single-frame components page is pushed as pixels, which takes the
        # panel off the hosted player: the memo still says "this digest is on
        # screen", so an animated page whose bytes did not change would be
        # skipped and the pushed page would stay there forever.
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(1, pixoo.play_gif.call_count)

        entity._render_components(
            pixoo, [{"type": "text", "content": "static page",
                     "position": [0, 0]}], {})
        pixoo.push_animation.assert_called_once()
        self.assertIsNone(entity._last_hosted_digest)

        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(2, pixoo.play_gif.call_count)

    def test_failed_play_forgets_the_digest_so_the_page_is_sent_again(self):
        # A failed play falls back to pushed frames, but the hosted player is
        # not what is on the panel: keep the digest and the next render of the
        # same bytes would leave the pushed page in place forever.
        entity, pixoo = self.make_entity()
        pixoo.play_gif.return_value = False
        self.play(entity, pixoo, [RED, GREEN])
        pixoo.push_animation.assert_called_once()
        self.assertIsNone(entity._last_hosted_digest)
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(2, pixoo.play_gif.call_count)

    def test_clock_page_forgets_the_digest_so_the_same_page_plays_again(self):
        # A stock dial takes the panel off our hosted player. The memo still
        # says "this digest is on screen", which is no longer true, so the next
        # render of the same bytes must play instead of being skipped.
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(1, pixoo.play_gif.call_count)
        entity._render_page({"page_type": "clock", "id": 12})
        self.assertIsNone(entity._last_hosted_digest)
        pixoo.set_clock.assert_called_once_with("12")
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(2, pixoo.play_gif.call_count)

    def test_gif_page_forgets_the_digest_so_the_same_page_plays_again(self):
        # A show_message gif preview is not our page: it takes the panel off the
        # hosted player, so the memo ("this digest is on screen") is stale and
        # the next components render must play instead of being skipped. Without
        # this the preview stayed on the panel until something else changed.
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(1, pixoo.play_gif.call_count)
        entity._render_page({"page_type": "gif",
                             "gif_url": "http://ha/local/other.gif"})
        self.assertIsNone(entity._last_hosted_digest)
        self.assertEqual("http://ha/local/other.gif",
                         pixoo.play_gif.call_args[0][0])
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(3, pixoo.play_gif.call_count)

    def test_channel_page_forgets_the_digest_so_the_same_page_plays_again(self):
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(1, pixoo.play_gif.call_count)
        entity._render_page({"page_type": "channel", "id": 0})
        self.assertIsNone(entity._last_hosted_digest)
        pixoo.set_custom_page.assert_called_once_with("0")
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(2, pixoo.play_gif.call_count)


class TestUnreachablePanel(HostedPageTest):
    def test_unavailable_panel_forgets_the_digest(self):
        # The panel rebooted (or dropped off the network): the entity goes
        # unavailable through the light's own update, and the next rotation
        # tick must not trust the digest, or an unchanged page is never
        # re-sent and the panel keeps showing nothing.
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        self.assertIsNotNone(entity._last_hosted_digest)
        entity.hass.data = {
            DOMAIN: {entity._config_entry.entry_id: {"available": False}}}
        entity.schedule_update_ha_state = mock.Mock()
        entity.async_schedule_next_page = mock.AsyncMock()

        asyncio.run(entity._async_next_page())

        self.assertIsNone(entity._last_hosted_digest)
        pixoo.play_gif.assert_called_once()  # no render while unavailable


class TestFallback(HostedPageTest):
    def test_push_animation_when_play_fails(self):
        entity, pixoo = self.make_entity()
        pixoo.play_gif.return_value = False
        self.play(entity, pixoo, [RED, GREEN])
        pixoo.push_animation.assert_called_once()
        self.assertEqual([self.page_url(entity)], self.played_urls(pixoo))

    def test_skip_keeps_the_page_matching_the_digest(self):
        entity, pixoo = self.make_entity()
        self.play(entity, pixoo, [RED, GREEN])
        page = self.pages_dir / entity._page_folder / HOSTED_PAGE_FILENAME
        first_bytes = page.read_bytes()
        self.play(entity, pixoo, [RED, GREEN])
        self.assertEqual(first_bytes, page.read_bytes())
        self.assertEqual(1, pixoo.play_gif.call_count)


if __name__ == "__main__":
    unittest.main()

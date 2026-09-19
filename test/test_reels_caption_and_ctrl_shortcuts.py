import logging
import unittest
from unittest.mock import MagicMock, patch

from InstaAddict.core.tui import (
    DashboardManager,
    DashboardState,
    KeyboardListenerThread,
)
from InstaAddict.core.utils import wait_for_next_session
from InstaAddict.core.views import PostsViewList
from InstaAddict.plugins.interact_reels import InteractReelsPlugin


class TestReelsCaptionExtraction(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        from InstaAddict.core.views import load_config
        mock_config = SimpleNamespace(
            args=SimpleNamespace(
                app_id="com.instagram.android",
                dont_type=False,
                watch_video_time="0",
                watch_photo_time="0",
                disable_block_detection=False,
            )
        )
        load_config(mock_config)

    def test_clean_trailing_more(self):
        """Verify _clean_trailing_more strips 'more' suffixes cleanly without mangling text."""
        clean = PostsViewList._clean_trailing_more
        self.assertEqual(clean("Hello world ...more"), "Hello world")
        self.assertEqual(clean("Puppies are cute... more"), "Puppies are cute")
        self.assertEqual(clean("Great day!\nmore"), "Great day!")
        self.assertEqual(clean("Nice post...more   "), "Nice post")
        self.assertEqual(clean("Tell me more about it"), "Tell me more about it")
        self.assertEqual(clean("Furthermore"), "Furthermore")
        self.assertEqual(clean(""), "")
        self.assertEqual(clean(None), "")

    def test_reels_caption_tier1_direct_container_text(self):
        """Tier 1: clips_caption container itself has text/description."""
        device = MagicMock()
        mock_caption_elem = MagicMock()
        mock_caption_elem.exists.return_value = True
        mock_caption_elem.get_desc.return_value = "Adorable golden retriever playing fetch #dogs"
        mock_caption_elem.get_text.return_value = None
        device.find.return_value = mock_caption_elem

        pvl = PostsViewList(device)
        pvl._post_owner = MagicMock(return_value=("retriever_owner", False, False))
        is_last, desc, username, is_ad, is_hashtag, has_tags = pvl._check_if_last_post(
            "prev_desc", "interact-reels"
        )
        self.assertEqual(desc, "ADORABLE GOLDEN RETRIEVER PLAYING FETCH #DOGS")
        self.assertEqual(username, "retriever_owner")

    def test_reels_caption_tier2_child_textview_when_container_is_empty_viewgroup(self):
        """Tier 2: clips_caption is a ViewGroup with empty get_desc/get_text, but child TextView has caption."""
        device = MagicMock()
        mock_caption_elem = MagicMock()
        mock_caption_elem.exists.return_value = True
        mock_caption_elem.get_desc.return_value = ""
        mock_caption_elem.get_text.return_value = ""

        # Child TextView inside ViewGroup
        child_text_elem = MagicMock()
        child_text_elem.exists.return_value = True
        child_text_elem.get_text.return_value = "Best coffee in town ☕ #coffeetime ...more"
        child_text_elem.get_desc.return_value = ""
        child_text_elem.count_items.return_value = 1

        # mock_caption_elem.child(...) returns the child_text_elem
        mock_caption_elem.child.return_value = child_text_elem
        device.find.return_value = mock_caption_elem

        pvl = PostsViewList(device)
        pvl._post_owner = MagicMock(return_value=("coffee_lover", False, False))
        is_last, desc, username, is_ad, is_hashtag, has_tags = pvl._check_if_last_post(
            "prev_desc", "interact-reels"
        )
        self.assertEqual(desc, "BEST COFFEE IN TOWN ☕ #COFFEETIME")

    def test_reels_caption_tier2b_child_textviews_with_author_prefix(self):
        """Tier 2b: Multiple child elements where first is author username and second is caption body."""
        device = MagicMock()
        mock_caption_elem = MagicMock()
        mock_caption_elem.exists.return_value = True
        mock_caption_elem.get_desc.return_value = ""
        mock_caption_elem.get_text.return_value = ""

        # mock child(className=...) has count_items > 1
        child_tv = MagicMock()
        child_tv.exists.return_value = True
        child_tv.count_items.return_value = 2

        def mock_get_text(error=False, index=0):
            if index == 0:
                return "coffee_lover"
            return "Morning brew hits different today! ☕"

        child_tv.get_text.side_effect = mock_get_text
        mock_caption_elem.child.return_value = child_tv
        device.find.return_value = mock_caption_elem

        pvl = PostsViewList(device)
        pvl._post_owner = MagicMock(return_value=("coffee_lover", False, False))
        is_last, desc, username, is_ad, is_hashtag, has_tags = pvl._check_if_last_post(
            "prev_desc", "interact-reels"
        )
        self.assertEqual(desc, "MORNING BREW HITS DIFFERENT TODAY! ☕")

    def test_reels_caption_tier3_alternative_selectors(self):
        """Tier 3: Primary clips_caption does not exist; alternative selector provides caption."""
        device = MagicMock()

        def mock_find(**kwargs):
            elem = MagicMock()
            res_match = kwargs.get("resourceIdMatches", "")
            if "clips_caption_component" in res_match:
                elem.exists.return_value = False
            elif "video_caption" in res_match:
                elem.exists.return_value = True
                elem.get_desc.return_value = ""
                elem.get_text.return_value = "Sunset over the mountains 🏔️"
                elem.child.return_value.exists.return_value = False
                elem.find_elements.return_value = []
            else:
                elem.exists.return_value = False
            return elem

        device.find.side_effect = mock_find

        pvl = PostsViewList(device)
        pvl._post_owner = MagicMock(return_value=("mountain_guide", False, False))
        is_last, desc, username, is_ad, is_hashtag, has_tags = pvl._check_if_last_post(
            "prev_desc", "interact-reels"
        )
        self.assertEqual(desc, "SUNSET OVER THE MOUNTAINS 🏔️")

    def test_reels_caption_tier4_xml_hierarchy_fallback(self):
        """Tier 4: UIAutomator selectors fail, but dump_hierarchy() contains caption node."""
        device = MagicMock()
        # All device.find calls return non-existent elements
        mock_not_found = MagicMock()
        mock_not_found.exists.return_value = False
        device.find.return_value = mock_not_found
        device.get_info.return_value = {"displayHeight": 2400, "displayWidth": 1080}

        mock_xml = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
        <hierarchy rotation="0">
            <node index="0" text="" class="android.widget.FrameLayout" package="com.instagram.android" visible-to-user="true" bounds="[0,0][1080,2400]">
                <node index="0" text="traveler" resource-id="com.instagram.android:id/clips_author_name" class="android.widget.TextView" visible-to-user="true" bounds="[50,1100][300,1150]" />
                <node index="1" text="Exploring hidden gems in Bali! 🌴 #travel" resource-id="com.instagram.android:id/clips_caption_text" class="android.widget.TextView" visible-to-user="true" bounds="[50,1200][800,1300]" />
            </node>
        </hierarchy>"""
        device.deviceV2.dump_hierarchy.return_value = mock_xml

        pvl = PostsViewList(device)
        caption = pvl._find_reels_caption_from_hierarchy(username="traveler")
        self.assertEqual(caption, "Exploring hidden gems in Bali! 🌴 #travel")


class TestCtrlShortcutsAndTui(unittest.TestCase):
    def setUp(self):
        self.mgr = DashboardManager.get_instance()
        self.mgr.state = DashboardState()

    def test_dashboard_state_upload_requested(self):
        """Verify is_upload_requested and consume_upload_request lifecycle."""
        state = self.mgr.state
        self.assertFalse(state.is_upload_requested())
        self.assertFalse(state.consume_upload_request())

        state.upload_requested = True
        self.assertTrue(state.is_upload_requested())
        self.assertTrue(state.consume_upload_request())
        self.assertFalse(state.is_upload_requested())

    def test_keyboard_listener_ctrl_u(self):
        """Verify CTRL+U key handling with control characters and character fallback."""
        listener = KeyboardListenerThread(self.mgr)
        with patch.object(self.mgr, "trigger_upload_request") as mock_upload:
            listener._handle_key(b"\x15")
            mock_upload.assert_called_once()

            listener._handle_key("\x15")
            self.assertEqual(mock_upload.call_count, 2)

            listener._handle_key("u")
            self.assertEqual(mock_upload.call_count, 3)

            listener._handle_key("U")
            self.assertEqual(mock_upload.call_count, 4)

    def test_keyboard_listener_ctrl_s(self):
        """Verify CTRL+S key handling with control characters and character fallback."""
        listener = KeyboardListenerThread(self.mgr)
        with patch.object(self.mgr, "trigger_skip_task") as mock_skip:
            listener._handle_key(b"\x13")
            mock_skip.assert_called_once()

            listener._handle_key("\x13")
            self.assertEqual(mock_skip.call_count, 2)

            listener._handle_key("s")
            self.assertEqual(mock_skip.call_count, 3)

            listener._handle_key("S")
            self.assertEqual(mock_skip.call_count, 4)

    def test_keyboard_listener_ctrl_d_debug_toggle(self):
        """Verify CTRL+D toggles root logger level between DEBUG and INFO dynamically."""
        listener = KeyboardListenerThread(self.mgr)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # Trigger CTRL+D -> DEBUG
        listener._handle_key(b"\x04")
        self.assertEqual(root_logger.level, logging.DEBUG)

        # Trigger CTRL+D -> INFO
        listener._handle_key(b"\x04")
        self.assertEqual(root_logger.level, logging.INFO)

    @patch("InstaAddict.core.utils.sleep")
    def test_wait_for_next_session_responsive_upload_wakeup(self, mock_sleep):
        """Verify wait_for_next_session wakes up immediately when upload_requested is armed."""
        from datetime import timedelta
        with patch.object(DashboardManager, "is_active", return_value=True):
            self.mgr.state.upload_requested = True
            device = MagicMock()
            session_state = MagicMock()
            sessions = [session_state]
            wait_for_next_session(timedelta(seconds=60), session_state, sessions, device)
            self.assertEqual(mock_sleep.call_count, 1)

    @patch("InstaAddict.plugins.interact_reels.TabBarView")
    @patch("InstaAddict.plugins.interact_reels.UniversalActions")
    def test_interact_reels_upload_requested_break(self, mock_actions, mock_tab_bar):
        """Verify interact_reels breaks loop early when upload_requested is armed."""
        plugin = InteractReelsPlugin()
        device = MagicMock()
        device.deviceV2.info = {"displayWidth": 1080, "displayHeight": 2400}
        device.deviceV2.screenshot.return_value = b"fake"
        device.find.return_value.exists.return_value = False
        mock_actions.escape_in_app_browser.return_value = False

        configs = MagicMock()
        configs.args.interact_reels = "10"
        configs.args.evaluate_percentage = 0
        configs.args.reels_topic = "dogs"

        session = MagicMock()
        session.totalWatched = 0

        with patch.object(DashboardManager, "is_active", return_value=True):
            # Pre-arm upload request
            self.mgr.state.upload_requested = True
            plugin.run(device, configs, None, [session], None, "interact-reels")

            # Should break after watching 0 or 1 reels (immediately on first loop check)
            self.assertEqual(session.totalWatched, 0)


if __name__ == "__main__":
    unittest.main()

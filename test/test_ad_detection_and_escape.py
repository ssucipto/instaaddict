import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from InstaAddict.core.views import (
    UniversalActions,
    PostsViewList,
    Owner,
    load_config,
)


class TestAdDetectionAndEscape(unittest.TestCase):
    def setUp(self):
        # Set up a mock config for views
        self.mock_config = SimpleNamespace(
            args=SimpleNamespace(
                app_id="com.instagram.android",
                dont_type=False,
                watch_video_time="0",
                watch_photo_time="0",
                disable_block_detection=False,
            )
        )
        load_config(self.mock_config)

    def test_escape_in_app_browser_detects_activity(self):
        device = MagicMock()
        device.app_id = "com.instagram.android"
        browser_act = (
            "com.instagram.inappbrowser.fragments"
            ".BrowserLiteInMainProcessIGActivity"
        )
        device.deviceV2.app_current.return_value = {
            "package": "com.instagram.android",
            "activity": browser_act,
            "pid": 1234,
        }

        # Mock close button exists
        close_btn = MagicMock()
        close_btn.exists.return_value = True
        device.find.return_value = close_btn

        with patch("InstaAddict.core.views.random_sleep"):
            escaped = UniversalActions.escape_in_app_browser(device)

        self.assertTrue(escaped)
        close_btn.click.assert_called()

    def test_escape_in_app_browser_detects_foreign_package(self):
        device = MagicMock()
        device.app_id = "com.instagram.android"
        device.deviceV2.app_current.return_value = {
            "package": "com.android.chrome",
            "activity": "org.chromium.chrome.browser.ChromeTabbedActivity",
            "pid": 5678,
        }

        # Mock no close button, fall back to back
        mock_ui = MagicMock()
        mock_ui.exists.return_value = False
        device.find.return_value = mock_ui

        with patch("InstaAddict.core.views.random_sleep"):
            escaped = UniversalActions.escape_in_app_browser(device)

        self.assertTrue(escaped)
        device.back.assert_called()

    def test_escape_in_app_browser_noop_on_main_activity(self):
        device = MagicMock()
        device.app_id = "com.instagram.android"
        device.deviceV2.app_current.return_value = {
            "package": "com.instagram.android",
            "activity": ".activity.MainTabActivity",
            "pid": 14808,
        }

        mock_ui = MagicMock()
        mock_ui.exists.return_value = False
        device.find.return_value = mock_ui

        escaped = UniversalActions.escape_in_app_browser(device)
        self.assertFalse(escaped)
        device.back.assert_not_called()

    def test_check_if_ad_by_cta_button(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        post_owner_obj = MagicMock()
        post_owner_obj.get_text.return_value = "brand_promo"
        post_owner_obj.get_desc.return_value = None
        ad_like_obj = MagicMock()
        ad_like_obj.exists.return_value = False
        post_owner_obj.sibling.return_value = ad_like_obj

        # Device finds CTA button
        cta_button = MagicMock()
        cta_button.exists.return_value = True
        device.find.return_value = cta_button

        is_ad, is_hashtag, owner_name = post_view._check_if_ad_or_hashtag(
            post_owner_obj
        )
        self.assertTrue(is_ad)
        self.assertEqual(owner_name, "brand_promo")

    def test_check_if_ad_by_sponsored_label(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        post_owner_obj = MagicMock()
        post_owner_obj.get_text.return_value = "sponsored_account"
        post_owner_obj.get_desc.return_value = None

        ad_like_obj = MagicMock()
        ad_like_obj.exists.return_value = True
        ad_like_obj.get_text.return_value = "Sponsored"
        post_owner_obj.sibling.return_value = ad_like_obj

        cta_button = MagicMock()
        cta_button.exists.return_value = False
        device.find.return_value = cta_button

        is_ad, is_hashtag, owner_name = post_view._check_if_ad_or_hashtag(
            post_owner_obj
        )
        self.assertTrue(is_ad)
        self.assertFalse(is_hashtag)

    def test_post_owner_open_refuses_ad_click(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        post_owner_obj = MagicMock()
        post_owner_obj.exists.return_value = True
        device.find.return_value = post_owner_obj

        with patch.object(
            post_view,
            "_check_if_ad_or_hashtag",
            return_value=(True, False, "sponsored_page"),
        ):
            opened, is_ad, is_hashtag = post_view._post_owner(
                "hashtag-posts-recent", Owner.OPEN
            )

        self.assertFalse(opened)
        self.assertTrue(is_ad)
        post_owner_obj.click.assert_not_called()

    def test_check_if_last_post_fast_exit_on_ad(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        with patch.object(
            post_view, "_post_owner", return_value=("ad_brand", True, False)
        ), patch.object(post_view, "_has_tags", return_value=False):
            is_same, desc, author, is_ad, is_hashtag, has_tags = (
                post_view._check_if_last_post(
                    "PREV_DESC", "hashtag-posts-recent"
                )
            )

        self.assertTrue(is_ad)
        self.assertEqual(desc, "")
        self.assertEqual(author, "")

    def test_check_if_last_post_fast_exit_on_empty_author(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        with patch.object(
            post_view, "_post_owner", return_value=(False, False, False)
        ), patch.object(post_view, "_has_tags", return_value=False):
            is_same, desc, author, is_ad, is_hashtag, has_tags = (
                post_view._check_if_last_post(
                    "PREV_DESC", "hashtag-posts-recent"
                )
            )

        self.assertFalse(is_ad)
        self.assertEqual(desc, "")
        self.assertEqual(author, "")

    def test_escape_in_app_browser_handles_none_app_current(self):
        device = MagicMock()
        device.app_id = "com.instagram.android"
        device.deviceV2.app_current.return_value = None

        mock_ui = MagicMock()
        mock_ui.exists.return_value = False
        device.find.return_value = mock_ui

        escaped = UniversalActions.escape_in_app_browser(device)
        self.assertFalse(escaped)

    def test_escape_in_app_browser_ignores_system_ui(self):
        device = MagicMock()
        device.app_id = "com.instagram.android"
        device.deviceV2.app_current.return_value = {
            "package": "com.android.systemui",
            "activity": "com.android.systemui.SomewhatActivity",
            "pid": 999,
        }

        mock_ui = MagicMock()
        mock_ui.exists.return_value = False
        device.find.return_value = mock_ui

        escaped = UniversalActions.escape_in_app_browser(device)
        self.assertFalse(escaped)

    def test_check_if_ad_ignores_cta_button_above_post_header(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        post_owner_obj = MagicMock()
        post_owner_obj.exists.return_value = True
        post_owner_obj.get_text.return_value = "organic_account"
        post_owner_obj.get_desc.return_value = None
        post_owner_obj.get_bounds.return_value = {
            "top": 500,
            "bottom": 580,
            "left": 0,
            "right": 1080,
        }

        ad_like_obj = MagicMock()
        ad_like_obj.exists.return_value = False
        post_owner_obj.sibling.return_value = ad_like_obj

        # Device finds CTA button, but it is ABOVE this post (e.g. bottom: 450)
        cta_button = MagicMock()
        cta_button.exists.return_value = True
        cta_button.get_bounds.return_value = {
            "top": 350,
            "bottom": 450,
            "left": 0,
            "right": 1080,
        }

        ad_text = MagicMock()
        ad_text.exists.return_value = False

        def mock_find(**kwargs):
            if "resourceIdMatches" in kwargs:
                return cta_button
            if "textMatches" in kwargs:
                return ad_text
            return MagicMock()

        device.find.side_effect = mock_find

        is_ad, is_hashtag, owner_name = post_view._check_if_ad_or_hashtag(
            post_owner_obj
        )
        self.assertFalse(is_ad)
        self.assertEqual(owner_name, "organic_account")

    def test_post_owner_open_refuses_empty_username(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        # post_owner_obj does not exist on screen initially
        post_owner_obj = MagicMock()
        post_owner_obj.exists.return_value = False
        device.find.return_value = post_owner_obj

        opened, is_ad, is_hashtag = post_view._post_owner(
            "hashtag-posts-recent", Owner.OPEN, username=""
        )
        self.assertFalse(opened)
        self.assertFalse(is_ad)


if __name__ == "__main__":
    unittest.main()

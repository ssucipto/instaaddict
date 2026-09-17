import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from InstaAddict.core.views import (
    UniversalActions,
    TabBarView,
    load_config,
)


class TestDialogDismissalAndStuckRecovery(unittest.TestCase):
    def setUp(self):
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

    def test_rate_instagram_dialog_clicks_no_thanks(self):
        """Verify that 'Rate Instagram' dialog strictly clicks 'No, thanks' and never 'Rate Instagram'."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        d = MagicMock()
        device.deviceV2 = d

        no_thanks_btn = MagicMock()
        no_thanks_btn.exists.return_value = True

        def d_call(**kwargs):
            text_match = kwargs.get("textMatches", "")
            mock_elem = MagicMock()
            if "No," in text_match or "No thanks" in text_match:
                return no_thanks_btn
            mock_elem.exists.return_value = False
            return mock_elem

        d.side_effect = d_call

        with patch("InstaAddict.core.views.random_sleep"):
            dismissed = UniversalActions.dismiss_dialog(device, max_sweeps=1)

        self.assertTrue(dismissed)
        no_thanks_btn.click.assert_called_once()

    def test_rate_instagram_dialog_clicks_remind_me_later_fallback(self):
        """Verify that if 'No, thanks' is absent, 'Remind me later' is clicked."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        d = MagicMock()
        device.deviceV2 = d

        remind_btn = MagicMock()
        remind_btn.exists.return_value = True

        def d_call(**kwargs):
            text_match = kwargs.get("textMatches", "")
            mock_elem = MagicMock()
            if "Remind" in text_match:
                return remind_btn
            mock_elem.exists.return_value = False
            return mock_elem

        d.side_effect = d_call

        with patch("InstaAddict.core.views.random_sleep"):
            dismissed = UniversalActions.dismiss_dialog(device, max_sweeps=1)

        self.assertTrue(dismissed)
        remind_btn.click.assert_called_once()

    def test_negative_dismiss_options_clicked(self):
        """Verify standard negative buttons like 'Not now', 'Cancel', 'Skip' are clicked."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        d = MagicMock()
        device.deviceV2 = d

        not_now_btn = MagicMock()
        not_now_btn.exists.return_value = True
        not_now_btn.info = {"text": "Not now"}

        def d_call(**kwargs):
            text_match = kwargs.get("textMatches", "")
            mock_elem = MagicMock()
            if "Not now" in text_match:
                return not_now_btn
            mock_elem.exists.return_value = False
            return mock_elem

        d.side_effect = d_call

        with patch("InstaAddict.core.views.random_sleep"):
            dismissed = UniversalActions.dismiss_dialog(device, max_sweeps=1)

        self.assertTrue(dismissed)
        not_now_btn.click.assert_called_once()

    def test_informational_ok_options_clicked(self):
        """Verify informational consent buttons ('OK', 'Got it', 'Continue') are clicked."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        d = MagicMock()
        device.deviceV2 = d

        ok_btn = MagicMock()
        ok_btn.exists.return_value = True
        ok_btn.info = {"text": "OK"}

        def d_call(**kwargs):
            text_match = kwargs.get("textMatches", "")
            mock_elem = MagicMock()
            if "^(OK|" in text_match or "Got it" in text_match:
                return ok_btn
            mock_elem.exists.return_value = False
            return mock_elem

        d.side_effect = d_call

        with patch("InstaAddict.core.views.random_sleep"):
            dismissed = UniversalActions.dismiss_dialog(device, max_sweeps=1)

        self.assertTrue(dismissed)
        ok_btn.click.assert_called_once()

    def test_system_anr_dialog_wait_clicked(self):
        """Verify Android system 'Instagram isn't responding' -> 'Wait' is clicked."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        d = MagicMock()
        device.deviceV2 = d

        wait_btn = MagicMock()
        wait_btn.exists.return_value = True

        def d_call(**kwargs):
            text_match = kwargs.get("textMatches", "")
            mock_elem = MagicMock()
            if "^Wait$" in text_match:
                return wait_btn
            mock_elem.exists.return_value = False
            return mock_elem

        d.side_effect = d_call

        with patch("InstaAddict.core.views.random_sleep"):
            dismissed = UniversalActions.dismiss_dialog(device, max_sweeps=1)

        self.assertTrue(dismissed)
        wait_btn.click.assert_called_once()

    def test_dismiss_dialog_returns_false_when_no_dialogs(self):
        """Verify False is returned when no popups exist, without throwing."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        d = MagicMock()
        device.deviceV2 = d

        mock_elem = MagicMock()
        mock_elem.exists.return_value = False
        d.return_value = mock_elem
        device.find.return_value = mock_elem

        dismissed = UniversalActions.dismiss_dialog(device, max_sweeps=2)
        self.assertFalse(dismissed)

    def test_stacked_dialog_dismissal_sweeps_multiple_times(self):
        """Verify stacked dialogs (e.g. Rate Instagram, then Notifications) are both dismissed in sweeps."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        d = MagicMock()
        device.deviceV2 = d

        pass_count = {"calls": 0}
        rate_btn = MagicMock()
        rate_btn.exists.return_value = True
        not_now_btn = MagicMock()
        not_now_btn.exists.return_value = True
        not_now_btn.info = {"text": "Not now"}

        def d_call(**kwargs):
            text_match = kwargs.get("textMatches", "")
            mock_elem = MagicMock()
            mock_elem.exists.return_value = False

            if pass_count["calls"] == 0:
                # First pass: Rate dialog present
                if "No," in text_match:
                    return rate_btn
            elif pass_count["calls"] == 1:
                # Second pass: Notification dialog present
                if "Not now" in text_match:
                    return not_now_btn
            return mock_elem

        rate_btn.click.side_effect = lambda: pass_count.update({"calls": 1})
        not_now_btn.click.side_effect = lambda: pass_count.update({"calls": 2})
        d.side_effect = d_call

        with patch("InstaAddict.core.views.random_sleep"):
            dismissed = UniversalActions.dismiss_dialog(device, max_sweeps=3)

        self.assertTrue(dismissed)
        rate_btn.click.assert_called_once()
        not_now_btn.click.assert_called_once()
        self.assertEqual(pass_count["calls"], 2)

    def test_recover_stuck_screen_escalation(self):
        """Verify stuck screen recovery executes dialog dismiss, back keys, Home check, and app restart."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        d = MagicMock()
        device.deviceV2 = d

        home_elem = MagicMock()
        home_elem.exists.return_value = False
        d.return_value = home_elem

        with patch.object(UniversalActions, "dismiss_dialog", return_value=True), \
             patch("InstaAddict.core.views.random_sleep"):
            result = UniversalActions.recover_stuck_screen(device, "com.instagram.android")

        self.assertTrue(result)
        device.back.assert_called_once()
        d.app_stop.assert_called_once_with("com.instagram.android")
        d.app_start.assert_called_once_with("com.instagram.android")

    def test_navigate_to_profile_recovers_when_dialog_obscures_tab(self):
        """Verify _navigateTo recovers tab lookup after dismissing obstructing dialog."""
        device = MagicMock()
        device.app_id = "com.instagram.android"
        tab_bar_view = TabBarView(device)

        profile_btn = MagicMock()
        profile_btn.exists.return_value = True

        call_state = {"dismissed": False}

        def mock_find(**kwargs):
            resource_match = kwargs.get("resourceIdMatches", "")
            mock_res = MagicMock()
            if "profile_tab" in str(resource_match):
                if call_state["dismissed"]:
                    return profile_btn
                mock_res.exists.return_value = False
                return mock_res
            mock_res.exists.return_value = False
            return mock_res

        device.find.side_effect = mock_find

        def mock_dismiss(dev):
            call_state["dismissed"] = True
            return True

        with patch.object(UniversalActions, "dismiss_dialog", side_effect=mock_dismiss), \
             patch.object(UniversalActions, "close_keyboard"):
            tab_bar_view.navigateToProfile()

        profile_btn.click.assert_called()

    def test_upload_to_ig_triggers_post_upload_dialog_sweep(self):
        """Verify _upload_to_ig executes post-upload dialog sweep after upload succeeds."""
        from InstaAddict.plugins.upload_posts import UploadPostsPlugin
        plugin = UploadPostsPlugin()
        device = MagicMock()
        d = MagicMock()
        device.deviceV2 = d
        device.device_id = "emulator-5554"

        device.deviceV2.serial = "emulator-5554"

        d_elem = MagicMock()
        d_elem.exists.return_value = True
        d.return_value = d_elem

        with patch("InstaAddict.core.views.UniversalActions.dismiss_dialog") as mock_dismiss, \
             patch.object(plugin, "_execute_adb", return_value=True), \
             patch.object(plugin, "_get_mediastore_id", return_value="123"), \
             patch("InstaAddict.plugins.upload_posts.random_sleep"), \
             patch("time.sleep"):
            success = plugin._upload_to_ig(
                device=device,
                media_path="test.jpg",
                caption="Test caption",
            )

        self.assertTrue(success)
        mock_dismiss.assert_called()


if __name__ == "__main__":
    unittest.main()

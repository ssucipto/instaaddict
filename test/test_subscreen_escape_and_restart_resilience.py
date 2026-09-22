import json
import unittest
from unittest.mock import MagicMock, patch

from InstaAddict.core.views import HomeView, TabBarView, SearchView, TabBarTabs
from uiautomator2.exceptions import UiObjectNotFoundError


class TestSubscreenEscapeAndRestartResilience(unittest.TestCase):
    def setUp(self):
        import InstaAddict.core.views as views
        from InstaAddict.core.resources import ResourceID as resources
        views.ResourceID = resources("com.instagram.android")
        self.device = MagicMock()

    def test_subscreen_auto_escape_already_visible(self):
        tab_bar = TabBarView(self.device)
        with patch.object(tab_bar, "is_tab_bar_visible", return_value=True):
            result = tab_bar._escape_subscreens()
            self.assertTrue(result)
            self.device.back.assert_not_called()

    @patch("InstaAddict.core.views.random_sleep", return_value=None)
    @patch("InstaAddict.core.views.UniversalActions.dismiss_dialog", return_value=False)
    def test_subscreen_auto_escape_restores_tab_bar_via_back_button(
        self, mock_dismiss, mock_sleep
    ):
        tab_bar = TabBarView(self.device)
        # Sequence: initial check False, then True after back button click
        with patch.object(
            tab_bar, "is_tab_bar_visible", side_effect=[False, True]
        ):
            back_btn = MagicMock()
            back_btn.exists.return_value = True
            self.device.find.return_value = back_btn

            result = tab_bar._escape_subscreens(max_attempts=3)
            self.assertTrue(result)
            back_btn.click.assert_called_once()
            self.device.back.assert_not_called()

    @patch("InstaAddict.core.views.random_sleep", return_value=None)
    @patch("InstaAddict.core.views.UniversalActions.dismiss_dialog", return_value=False)
    def test_subscreen_auto_escape_restores_tab_bar_via_device_back(
        self, mock_dismiss, mock_sleep
    ):
        tab_bar = TabBarView(self.device)
        # Sequence: initial check False, then True after device.back()
        with patch.object(
            tab_bar, "is_tab_bar_visible", side_effect=[False, True]
        ):
            back_btn = MagicMock()
            back_btn.exists.return_value = False
            self.device.find.return_value = back_btn

            result = tab_bar._escape_subscreens(max_attempts=3)
            self.assertTrue(result)
            self.device.back.assert_called_once()

    @patch("InstaAddict.core.views.random_sleep", return_value=None)
    @patch("InstaAddict.core.views.UniversalActions.dismiss_dialog", return_value=False)
    def test_subscreen_auto_escape_max_attempts_exceeded(
        self, mock_dismiss, mock_sleep
    ):
        tab_bar = TabBarView(self.device)
        with patch.object(tab_bar, "is_tab_bar_visible", return_value=False):
            back_btn = MagicMock()
            back_btn.exists.return_value = False
            self.device.find.return_value = back_btn

            result = tab_bar._escape_subscreens(max_attempts=2)
            self.assertFalse(result)
            self.assertEqual(self.device.back.call_count, 2)

    @patch("InstaAddict.core.views.random_sleep", return_value=None)
    @patch("InstaAddict.core.views.UniversalActions.dismiss_dialog", return_value=True)
    def test_subscreen_auto_escape_via_dialog_dismissal(
        self, mock_dismiss, mock_sleep
    ):
        tab_bar = TabBarView(self.device)
        # Sequence: initial check False, then True after dialog dismissal
        with patch.object(tab_bar, "is_tab_bar_visible", side_effect=[False, True]):
            result = tab_bar._escape_subscreens(max_attempts=3)
            self.assertTrue(result)
            self.device.back.assert_not_called()

    @patch("InstaAddict.core.views.UniversalActions.close_keyboard")
    def test_navigate_to_search_triggers_escape_when_tab_bar_hidden(
        self, mock_close_kbd
    ):
        tab_bar = TabBarView(self.device)
        search_btn = MagicMock()
        search_btn.exists.return_value = True

        # When searching for tabs, return search_btn
        self.device.find.return_value = search_btn

        with patch.object(tab_bar, "is_tab_bar_visible", side_effect=[False, True]), \
                patch.object(tab_bar, "_escape_subscreens", return_value=True) as mock_escape:
            view = tab_bar.navigateToSearch()
            mock_escape.assert_called()
            self.assertIsInstance(view, SearchView)
            search_btn.click.assert_called()

    def test_home_view_navigate_to_search_guarded_when_missing(self):
        home_view = HomeView(self.device)
        search_btn = MagicMock()
        search_btn.exists.return_value = False
        home_view.action_bar.child.return_value = search_btn

        result = home_view.navigateToSearch()
        self.assertIsNone(result)
        search_btn.click.assert_not_called()

    def test_home_view_navigate_to_search_success(self):
        home_view = HomeView(self.device)
        search_btn = MagicMock()
        search_btn.exists.return_value = True
        home_view.action_bar.child.return_value = search_btn

        result = home_view.navigateToSearch()
        self.assertIsInstance(result, SearchView)
        search_btn.click.assert_called_once()

    @patch("InstaAddict.core.decorators.close_instagram")
    @patch("InstaAddict.core.decorators.check_if_crash_popup_is_there", return_value=False)
    @patch("InstaAddict.core.decorators.random_sleep")
    @patch("InstaAddict.core.decorators.open_instagram", return_value=True)
    @patch("InstaAddict.core.decorators.TabBarView")
    def test_restart_resilient_to_navigate_to_profile_retry_success(
        self, mock_tab_bar_cls, mock_open_ig, mock_sleep, mock_crash_popup, mock_close_ig
    ):
        from InstaAddict.core.decorators import restart

        mock_tab_bar_instance = MagicMock()
        # First call raises UiObjectNotFoundError, second call succeeds
        mock_tab_bar_instance.navigateToProfile.side_effect = [
            UiObjectNotFoundError({"code": -32001, "message": "PROFILE_TAB not found"}),
            MagicMock(),
        ]
        mock_tab_bar_cls.return_value = mock_tab_bar_instance

        sessions = [MagicMock()]
        session_state = MagicMock()
        configs = MagicMock()
        configs.args.count_app_crashes = False
        self.device.deviceV2.app_list_running.return_value = ["com.instagram.android"]

        # restart() should handle the exception, retry, and succeed without raising
        restart(
            self.device,
            sessions,
            session_state,
            configs,
            normal_crash=False,
            print_traceback=False,
        )
        self.assertEqual(mock_tab_bar_instance.navigateToProfile.call_count, 2)

    @patch("InstaAddict.core.decorators.close_instagram")
    @patch("InstaAddict.core.decorators.check_if_crash_popup_is_there", return_value=False)
    @patch("InstaAddict.core.decorators.random_sleep")
    @patch("InstaAddict.core.decorators.open_instagram", return_value=True)
    @patch("InstaAddict.core.decorators.TabBarView")
    def test_restart_resilient_when_profile_navigation_fails_completely(
        self, mock_tab_bar_cls, mock_open_ig, mock_sleep, mock_crash_popup, mock_close_ig
    ):
        from InstaAddict.core.decorators import restart

        mock_tab_bar_instance = MagicMock()
        # Both calls raise an exception
        mock_tab_bar_instance.navigateToProfile.side_effect = Exception("Persistent RPC Failure")
        mock_tab_bar_cls.return_value = mock_tab_bar_instance

        sessions = [MagicMock()]
        session_state = MagicMock()
        configs = MagicMock()
        configs.args.count_app_crashes = False
        self.device.deviceV2.app_list_running.return_value = ["com.instagram.android"]

        # restart() should catch both attempts, log error, and return without crashing
        restart(
            self.device,
            sessions,
            session_state,
            configs,
            normal_crash=False,
            print_traceback=False,
        )
        self.assertEqual(mock_tab_bar_instance.navigateToProfile.call_count, 2)

    @patch("InstaAddict.core.utils.check_if_crash_popup_is_there", return_value=False)
    @patch("InstaAddict.core.utils.choose_cloned_app")
    @patch("InstaAddict.core.utils.random_sleep")
    @patch("InstaAddict.core.utils.subprocess.run")
    def test_open_instagram_ui_settle_verification(
        self, mock_subproc, mock_random_sleep, mock_cloned, mock_crash_popup
    ):
        from InstaAddict.core.utils import open_instagram
        import InstaAddict.core.utils as utils_mod

        utils_mod.app_id = "com.instagram.android"
        configs = MagicMock()
        configs.args.close_apps = False
        configs.device_id = None
        utils_mod.configs = configs

        device = MagicMock()
        device.deviceV2.app_start.return_value = None
        device.deviceV2.app_current.return_value = {"package": "com.instagram.android"}
        mock_subproc.return_value = MagicMock(stdout="com.github.uiautomator/.FastInputIME")

        with patch("InstaAddict.core.views.TabBarView.is_tab_bar_visible", return_value=True) as mock_tab_vis, \
                patch("InstaAddict.core.views.UniversalActions.dismiss_dialog", return_value=False) as mock_dismiss:
            result = open_instagram(device)
            self.assertTrue(result)
            mock_tab_vis.assert_called()
            mock_dismiss.assert_called()

    def test_session_state_subscreen_escapes_telemetry_and_serialization(self):
        from InstaAddict.core.session_state import SessionState, SessionStateEncoder
        configs = MagicMock()
        configs.args = MagicMock()
        session = SessionState(configs)
        self.assertEqual(session.totalSubscreenEscapes, 0)
        session.increment_subscreen_escapes(3)
        self.assertEqual(session.totalSubscreenEscapes, 3)

        encoded = SessionStateEncoder().default(session)
        self.assertEqual(encoded.get("total_subscreen_escapes"), 3)

    @patch("InstaAddict.core.views.random_sleep", return_value=None)
    @patch("InstaAddict.core.views.UniversalActions.dismiss_dialog", return_value=False)
    def test_subscreen_escape_increments_session_state(
        self, mock_dismiss, mock_sleep
    ):
        from InstaAddict.core.session_state import SessionState
        configs = MagicMock()
        configs.args = MagicMock()
        session = SessionState(configs)
        SessionState.set_active(session)

        tab_bar = TabBarView(self.device)
        with patch.object(tab_bar, "is_tab_bar_visible", side_effect=[False, True]):
            back_btn = MagicMock()
            back_btn.exists.return_value = True
            self.device.find.return_value = back_btn

            result = tab_bar._escape_subscreens(max_attempts=3)
            self.assertTrue(result)
            self.assertEqual(session.totalSubscreenEscapes, 1)

        SessionState.set_active(None)

    def test_dogfood_optimizer_detects_subscreen_and_restart_failures(self):
        import os
        import tempfile
        from InstaAddict.core.dogfood import DogfoodOptimizer

        with tempfile.TemporaryDirectory() as temp_dir:
            username = "test_user"
            optimizer = DogfoodOptimizer(username)
            optimizer.account_dir = temp_dir
            optimizer.sessions_path = os.path.join(temp_dir, "sessions.json")
            optimizer.suggestions_json_path = os.path.join(
                temp_dir, "tuning_suggestions.json"
            )
            optimizer.suggestions_md_path = os.path.join(
                temp_dir, "tuning_suggestions.md"
            )
            fake_log_path = os.path.join(temp_dir, "error_trace.log")
            optimizer.error_log_path = fake_log_path

            log_content = (
                "2026-09-20 00:01:00 WARNING Tab bar not visible (screen in subscreen). Attempting auto-escape...\n"
                "2026-09-20 00:01:05 WARNING Could not restore tab bar after 3 escape attempt(s).\n"
                "2026-09-20 00:01:10 ERROR Failed to navigate to profile after restart: UiObjectNotFoundError\n"
            )
            with open(fake_log_path, "w", encoding="utf-8") as f:
                f.write(log_content)

            with open(optimizer.sessions_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "total_interactions": 10,
                            "successful_interactions": 8,
                            "total_subscreen_escapes": 2,
                        }
                    ],
                    f,
                )

            report = optimizer.analyze()
            errs = report["error_diagnostics"]
            self.assertEqual(errs["subscreen_escapes"], 1)
            self.assertEqual(errs["subscreen_escape_failures"], 1)
            self.assertEqual(errs["restart_profile_failures"], 1)

            categories = [r["category"] for r in report["recommendations"]]
            self.assertIn("Navigation & Subscreens", categories)
            self.assertIn("Restart & Recovery", categories)
            self.assertEqual(report["metrics"]["total_subscreen_escapes"], 2)

    def test_tui_dashboard_state_sync_subscreen_escapes(self):
        from InstaAddict.core.tui import DashboardState

        state = DashboardState()
        mock_session = MagicMock()
        mock_session.totalSubscreenEscapes = 7
        mock_session.totalLikes = 10
        mock_session.totalFollowed = {}
        mock_session.totalUnfollowed = 0
        mock_session.totalComments = 0
        mock_session.totalWatched = 0
        mock_session.totalUploadsSuccess = 0
        mock_session.totalUploadsFailed = 0
        mock_session.totalCrashes = 0
        mock_session.totalInteractions = {}
        mock_session.totalPostsChecked = 0
        mock_session.totalProfilesChecked = 0
        mock_session.totalProfilesSkipped = 0
        mock_session.totalAdsBypassed = 0
        mock_session.totalDialogsDismissed = 0
        mock_session.totalReelsEvaluated = 0
        mock_session.totalWatchdogRecoveries = 0
        mock_session.uploadHistory = []

        state.update_from_session_state(mock_session)
        self.assertEqual(state.subscreen_escapes, 7)

    @patch("InstaAddict.core.views.UniversalActions.close_keyboard")
    @patch("InstaAddict.core.views.random_sleep", return_value=None)
    @patch("InstaAddict.core.views.UniversalActions.dismiss_dialog", return_value=False)
    def test_tab_bar_navigate_to_all_tabs_symmetry(
        self, mock_dismiss, mock_sleep, mock_close_kbd
    ):
        tab_bar = TabBarView(self.device)

        # Test retry resolution for ORDERS and ACTIVITY
        for tab in (TabBarTabs.ORDERS, TabBarTabs.ACTIVITY):
            with patch.object(tab_bar, "is_tab_bar_visible", return_value=True):
                btn = MagicMock()
                # first lookup fails, exists(MEDIUM) fails, retry succeeds
                btn.exists.side_effect = [False, True, True]
                self.device.find.return_value = btn
                tab_bar._navigateTo(tab)
                btn.click.assert_called()


if __name__ == "__main__":
    unittest.main()

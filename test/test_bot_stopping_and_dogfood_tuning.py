"""
Unit tests for Audit #131:
- Android Keyguard screen unlock & dumpsys parsing
- Resilient unlock flow with native dismiss-keyguard & keyevent fallbacks
- SessionState & Rich Summary username initialization without @unknown fallback
- Atomic task skip consumption preventing cascade task skips
- HashtagManager two-strike dead tag pruning guard
- ActionUnfollowFollowers cache saturation breakout
- DogfoodOptimizer recommendations for COOLDOWN starvation and unfollow direction
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from InstaAddict.core.device_facade import DeviceFacade
from InstaAddict.core.session_state import SessionState
from InstaAddict.core.tui import DashboardState
from InstaAddict.core.hashtag_manager import HashtagManager
from InstaAddict.core.dogfood import DogfoodOptimizer


class TestDeviceUnlockAndLockscreen(unittest.TestCase):
    def setUp(self):
        self.device = DeviceFacade.__new__(DeviceFacade)
        self.device.deviceV2 = MagicMock()
        self.device.deviceV2.serial = "emulator-5554"

    @patch("InstaAddict.core.device_facade.run")
    def test_is_screen_locked_modern_android(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "mShowingDream=false\nisKeyguardShowing=true\nmDreamingLockscreen=false\n"
        mock_run.return_value = mock_proc

        self.assertTrue(self.device.is_screen_locked())

    @patch("InstaAddict.core.device_facade.run")
    def test_is_screen_unlocked_modern_android(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "mShowingDream=false\nisKeyguardShowing=false\nmDreamingLockscreen=false\n"
        mock_run.return_value = mock_proc

        self.assertFalse(self.device.is_screen_locked())

    @patch("InstaAddict.core.device_facade.run")
    def test_is_screen_locked_legacy_android(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "mDreamingLockscreen=true\n"
        mock_run.return_value = mock_proc

        self.assertTrue(self.device.is_screen_locked())

    @patch("InstaAddict.core.device_facade.sleep")
    @patch("InstaAddict.core.device_facade.run")
    def test_unlock_invokes_native_dismiss_and_keyevents(self, mock_run, mock_sleep):
        mock_proc_locked = MagicMock()
        mock_proc_locked.stdout = "isKeyguardShowing=false\n"
        mock_run.return_value = mock_proc_locked

        with patch.object(self.device, "swipe") as mock_swipe:
            self.device.unlock()

            calls = [call[0][0] for call in mock_run.call_args_list]
            self.assertTrue(any("wm" in cmd and "dismiss-keyguard" in cmd for cmd in calls))
            self.assertTrue(any("input" in cmd and "224" in cmd for cmd in calls))
            self.assertTrue(any("input" in cmd and "82" in cmd for cmd in calls))

            mock_swipe.assert_not_called()


class TestSessionStateAndSummaryUsername(unittest.TestCase):
    def test_session_state_initializes_username_from_configs(self):
        mock_configs = MagicMock()
        mock_configs.args.username = "lolatheozjack"

        ss = SessionState(mock_configs)
        self.assertEqual(ss.my_username, "lolatheozjack")

    def test_session_state_defaults_none_when_no_username(self):
        mock_configs = MagicMock()
        mock_configs.args = MagicMock(spec=[])

        ss = SessionState(mock_configs)
        self.assertIsNone(ss.my_username)


class TestAtomicTaskSkipConsumption(unittest.TestCase):
    def test_consume_skip_task_request_clears_flag(self):
        state = DashboardState(username="testuser")
        state.trigger_skip_task()

        self.assertTrue(state.is_skip_task_requested())
        self.assertTrue(state.consume_skip_task_request())
        self.assertFalse(state.is_skip_task_requested())
        self.assertFalse(state.consume_skip_task_request())

    def test_consume_skip_task_removes_file(self):
        user_dir = os.path.join("accounts", "tempuser_test_skip")
        os.makedirs(user_dir, exist_ok=True)
        sig_file = os.path.join(user_dir, ".skip_task")
        try:
            with open(sig_file, "w") as f:
                f.write("123")

            state = DashboardState(username="tempuser_test_skip")
            self.assertTrue(state.is_skip_task_requested())
            self.assertTrue(state.consume_skip_task_request())
            self.assertFalse(os.path.exists(sig_file))
            self.assertFalse(state.is_skip_task_requested())
        finally:
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)


class TestHashtagManagerPruningGuards(unittest.TestCase):
    def test_record_hashtag_result_requires_two_strikes_before_dead(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HashtagManager(username="testhash", account_dir=tmpdir)
            mgr.master_data = {
                "version": "1.0.0",
                "username": "testhash",
                "tiers": {
                    "tier1": {"tags": ["jackrussell", "dogsofperth"]}
                },
                "dead_tags": []
            }

            # Strike 1: should not mark as DEAD
            mgr.record_hashtag_result("jackrussell", posts_found=False, strikes_needed=2)
            self.assertNotIn("jackrussell", mgr.master_data["dead_tags"])
            self.assertIn("jackrussell", mgr.master_data["tiers"]["tier1"]["tags"])
            self.assertEqual(mgr.master_data.get("zero_post_counts", {}).get("jackrussell"), 1)

            # Strike 2: should mark as DEAD and prune
            mgr.record_hashtag_result("jackrussell", posts_found=False, strikes_needed=2)
            self.assertIn("jackrussell", mgr.master_data["dead_tags"])
            self.assertNotIn("jackrussell", mgr.master_data["tiers"]["tier1"]["tags"])


class TestDogfoodOptimizerTuningRules(unittest.TestCase):
    def test_cooldown_starvation_recommendation(self):
        optimizer = DogfoodOptimizer(username="testuser")
        with patch.object(optimizer, "_load_sessions", return_value=[
            {
                "total_interactions": 30,
                "successful_interactions": 24,
                "skip_reasons": {
                    "COOLDOWN": 45,
                    "BIOGRAPHY_IS_EMPTY": 5,
                },
                "job_metrics": {},
                "crashes": 0,
            }
        ]), patch.object(optimizer, "_analyze_error_log", return_value={}):
            result = optimizer.analyze()
            recs = result.get("recommendations", [])
            cooldown_recs = [r for r in recs if r.get("parameter") == "can-reinteract-after"]
            self.assertTrue(len(cooldown_recs) > 0)
            self.assertEqual(cooldown_recs[0]["suggested_value"], "24")
            self.assertEqual(cooldown_recs[0]["severity"], "HIGH")

    def test_unfollow_saturation_recommendation(self):
        optimizer = DogfoodOptimizer(username="testuser")
        with patch.object(optimizer, "_load_sessions", return_value=[
            {
                "total_interactions": 30,
                "successful_interactions": 24,
                "skip_reasons": {},
                "job_metrics": {
                    "unfollow-non-followers": {
                        "interactions_attempted": 0,
                        "interactions_successful": 0,
                        "duration_seconds": 650.0,
                    }
                },
                "crashes": 0,
            }
        ]), patch.object(optimizer, "_analyze_error_log", return_value={}):
            result = optimizer.analyze()
            recs = result.get("recommendations", [])
            unfollow_recs = [r for r in recs if r.get("parameter") == "sort-followers-latest"]
            self.assertTrue(len(unfollow_recs) > 0)
            self.assertEqual(unfollow_recs[0]["suggested_value"], "true")


class TestBiographyFilterResilience(unittest.TestCase):
    def test_biography_empty_not_skipped_without_mandatory_words(self):
        from InstaAddict.core.filter import Filter, Profile, SkipReason
        filt = Filter.__new__(Filter)
        # Conditions with specific_alphabet only (like lolatheozjack), no mandatory words
        filt.conditions = {
            "specific_alphabet": ["LATIN"],
            "min_followers": 10,
            "max_followers": 10000,
            "min_followings": 10,
            "max_followings": 5000,
            "min_posts": 1,
        }
        filt.storage = MagicMock()
        profile_data = Profile(
            mutual_friends=0,
            follow_button_text="Follow",
            is_restricted=False,
            is_private=False,
            has_business_category=False,
            posts_count=5,
            biography="",  # Empty bio
            link_in_bio=None,
            fullname="John Doe",
        )
        profile_data.set_followers_and_following(100, 50)
        filt.get_all_data = MagicMock(return_value=profile_data)
        filt.return_check_profile = MagicMock(side_effect=lambda u, p, r: r is None)

        _, ok = filt.check_profile(MagicMock(), "testuser")
        self.assertTrue(ok)
        filt.return_check_profile.assert_called_with("testuser", profile_data, None)

    def test_biography_empty_skipped_when_mandatory_words_configured(self):
        from InstaAddict.core.filter import Filter, Profile, SkipReason
        filt = Filter.__new__(Filter)
        filt.conditions = {
            "mandatory_words": ["dog", "puppy"],
            "min_posts": 1,
        }
        filt.storage = MagicMock()
        profile_data = Profile(
            mutual_friends=0,
            follow_button_text="Follow",
            is_restricted=False,
            is_private=False,
            has_business_category=False,
            posts_count=5,
            biography="",
            link_in_bio=None,
            fullname="Dog Lover",
        )
        profile_data.set_followers_and_following(100, 50)
        filt.get_all_data = MagicMock(return_value=profile_data)
        filt.return_check_profile = MagicMock(side_effect=lambda u, p, r: r is None)

        _, ok = filt.check_profile(MagicMock(), "testuser")
        self.assertFalse(ok)
        filt.return_check_profile.assert_called_with("testuser", profile_data, SkipReason.BIOGRAPHY_IS_EMPTY)

    def test_biography_empty_skipped_when_skip_if_empty_biography_true(self):
        from InstaAddict.core.filter import Filter, Profile, SkipReason
        filt = Filter.__new__(Filter)
        filt.conditions = {
            "skip_if_empty_biography": True,
            "min_posts": 1,
        }
        filt.storage = MagicMock()
        profile_data = Profile(
            mutual_friends=0,
            follow_button_text="Follow",
            is_restricted=False,
            is_private=False,
            has_business_category=False,
            posts_count=5,
            biography="",
            link_in_bio=None,
            fullname="Dog Lover",
        )
        profile_data.set_followers_and_following(100, 50)
        filt.get_all_data = MagicMock(return_value=profile_data)
        filt.return_check_profile = MagicMock(side_effect=lambda u, p, r: r is None)

        _, ok = filt.check_profile(MagicMock(), "testuser")
        self.assertFalse(ok)
        filt.return_check_profile.assert_called_with("testuser", profile_data, SkipReason.BIOGRAPHY_IS_EMPTY)

    def test_find_alphabet_empty_string(self):
        from InstaAddict.core.filter import Filter
        self.assertEqual(Filter._find_alphabet(""), "")
        self.assertEqual(Filter._find_alphabet("🐶🐾✨"), "")
        self.assertEqual(Filter._find_alphabet("Lola the Dog"), "LATIN")


class TestDeviceFacadeResurrectionAndSelfHealing(unittest.TestCase):
    def test_ensure_uiautomator_alive_handles_gateway_error(self):
        device = DeviceFacade.__new__(DeviceFacade)
        device.deviceV2 = MagicMock()
        # First call to dump_hierarchy fails with GatewayError, second succeeds after resurrection
        device.deviceV2.dump_hierarchy.side_effect = [
            Exception("uiautomator2.GatewayError: gateway error, time used 1.1s"),
            "<hierarchy />",
        ]
        mock_shell_output = MagicMock()
        mock_shell_output.output = "instrumentation:com.github.uiautomator.test/androidx.test.runner.AndroidJUnitRunner"
        device.deviceV2.shell.return_value = mock_shell_output

        result = device.ensure_uiautomator_alive()
        self.assertTrue(result)
        # Verify shell was called to resurrect uiautomator
        self.assertTrue(device.deviceV2.shell.called)

    def test_view_exists_self_healing_on_rpc_error(self):
        mock_u2_device = MagicMock()
        mock_shell_output = MagicMock()
        mock_shell_output.output = "instrumentation:com.github.uiautomator.test/androidx.test.runner.AndroidJUnitRunner"
        mock_u2_device.shell.return_value = mock_shell_output

        mock_u2_view = MagicMock()
        mock_u2_view.exists.side_effect = [
            Exception("uiautomator2.GatewayError(gateway error, time used 1.1s)"),
            True,
        ]

        view = DeviceFacade.View(mock_u2_view, mock_u2_device)
        exists = view.exists(ui_timeout=1)
        self.assertTrue(exists)
        self.assertEqual(mock_u2_view.exists.call_count, 2)


if __name__ == "__main__":
    unittest.main()


import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

from InstaAddict.core.device_facade import Direction
from InstaAddict.core.gemini_vision import _safe_rate_limit_sleep
from InstaAddict.core.session_state import SessionState
from InstaAddict.core.utils import EmptyList, stop_bot


class TestMultiSessionResilience(unittest.TestCase):
    """Tests for multi-session daemon stability, watchdog heartbeat emission,

    graceful blogger followers error recovery, and finishTime stamping.
    """

    @patch("InstaAddict.core.watchdog.record_heartbeat")
    @patch("InstaAddict.core.watchdog.BotWatchdog.get_instance")
    @patch("time.sleep")
    def test_safe_rate_limit_sleep_watchdog_pause_and_heartbeat(
        self, mock_sleep, mock_get_watchdog, mock_record_heartbeat
    ):
        """Verify _safe_rate_limit_sleep pauses watchdog, sleeps in chunks,

        emits heartbeats, and resumes watchdog cleanly.
        """
        mock_watchdog = MagicMock()
        mock_get_watchdog.return_value = mock_watchdog

        # Sleep for 12 seconds -> chunks: 5, 5, 2
        _safe_rate_limit_sleep(wait_time=12, attempt=0, max_retries=3, context="Unit Test")

        mock_watchdog.pause.assert_called_once()
        mock_watchdog.resume.assert_called_once()

        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_has_calls([call(5), call(5), call(2)])

        self.assertEqual(mock_record_heartbeat.call_count, 3)
        self.assertTrue(
            all(c[0][0] == "gemini_vision" for c in mock_record_heartbeat.call_args_list)
        )

    def test_stop_bot_stamps_finish_time_if_none(self):
        """Verify stop_bot sets finishTime if None, ensuring is_finished() returns True."""
        mock_device = MagicMock()
        mock_sessions = MagicMock()
        mock_session_state = SessionState()
        self.assertIsNone(mock_session_state.finishTime)
        self.assertFalse(mock_session_state.is_finished())

        with patch("InstaAddict.core.utils.print_full_report"), \
             patch("InstaAddict.core.utils.close_instagram"), \
             patch("InstaAddict.core.utils.ask_for_a_donation"), \
             patch("sys.exit") as mock_exit:
            stop_bot(mock_device, mock_sessions, mock_session_state)
            mock_exit.assert_called_with(2)

        self.assertIsNotNone(mock_session_state.finishTime)
        self.assertTrue(mock_session_state.is_finished())
        self.assertIsInstance(mock_session_state.finishTime, datetime)

    @patch("InstaAddict.core.watchdog.record_heartbeat")
    def test_handle_followers_empty_list_graceful_return(self, mock_heartbeat):
        """Verify iterate_over_followers gracefully returns without raising on EmptyList."""
        from InstaAddict.core.handle_sources import iterate_over_followers

        mock_plugin = MagicMock()
        mock_plugin.ResourceID.FOLLOW_LIST_CONTAINER = "follow_container"
        mock_plugin.ResourceID.ROW_SEARCH_EDIT_TEXT = "search_edit"
        mock_plugin.ResourceID.USER_LIST_CONTAINER = "user_list"

        mock_device = MagicMock()
        # Find follow list container wait
        mock_container = MagicMock()
        mock_device.find.return_value = mock_container

        mock_storage = MagicMock()
        mock_session_state = SessionState()

        with patch("InstaAddict.core.handle_sources.inspect_current_view", side_effect=EmptyList), \
             patch("InstaAddict.core.handle_sources.check_and_report_restricted_list", return_value=False), \
             patch("InstaAddict.core.handle_sources.random_sleep"):
            # Should NOT raise EmptyList, must return gracefully
            try:
                iterate_over_followers(
                    self=mock_plugin,
                    device=mock_device,
                    interaction=MagicMock(),
                    is_follow_limit_reached=MagicMock(return_value=False),
                    storage=mock_storage,
                    on_interaction=MagicMock(),
                    is_myself=False,
                    scroll_end_detector=MagicMock(),
                    session_state=mock_session_state,
                    current_job="blogger-followers",
                    target="testblogger",
                )
            except EmptyList:
                self.fail("iterate_over_followers raised EmptyList instead of returning gracefully!")

        # Verified device.back() was called to return to blogger profile
        self.assertTrue(mock_device.back.called)
        # Heartbeat was recorded
        mock_heartbeat.assert_called_with("blogger-followers", "Iterating followers for @testblogger")

    @patch("InstaAddict.core.watchdog.record_heartbeat")
    def test_unfollow_heartbeat_and_transient_get_text_error(self, mock_heartbeat):
        """Verify action_unfollow_followers emits heartbeats and safely skips transient get_text errors."""
        from InstaAddict.plugins.action_unfollow_followers import (
            ActionUnfollowFollowers,
            UnfollowRestriction,
        )

        plugin = ActionUnfollowFollowers()
        plugin.args = MagicMock()
        plugin.args.unfollow_any = True
        plugin.args.ignore_followers_cache = True
        plugin.ResourceID = MagicMock()
        plugin.session_state = SessionState()
        plugin.no_unfollow_option = []

        mock_device = MagicMock()
        mock_device.get_info.return_value = {"displayWidth": 1080, "displayHeight": 2400}
        mock_storage = MagicMock()
        mock_storage.is_user_in_whitelist.return_value = False
        mock_storage.is_non_bot_following.return_value = False
        mock_storage.get_following_status.return_value = MagicMock()

        # Row item 1 raises Exception on get_text(), Row item 2 succeeds
        mock_item1 = MagicMock()
        mock_item1.get_height.return_value = 100
        mock_user_view1 = MagicMock()
        mock_user_view1.exists.return_value = True
        mock_user_view1.get_text.side_effect = Exception("UI element recycled")
        mock_item1.child.return_value = mock_user_view1

        mock_item2 = MagicMock()
        mock_item2.get_height.return_value = 100
        mock_user_view2 = MagicMock()
        mock_user_view2.exists.return_value = True
        mock_user_view2.get_text.return_value = "valid_user"
        mock_item2.child.return_value = mock_user_view2

        mock_user_list = [mock_item1, mock_item2]
        mock_container = MagicMock()
        mock_container.exists.return_value = False

        def find_side_effect(**kwargs):
            if "resourceIdMatches" in kwargs:
                return mock_user_list
            return mock_container

        mock_device.find.side_effect = find_side_effect

        with patch("InstaAddict.plugins.action_unfollow_followers.inspect_current_view", return_value=(100, 2)), \
             patch.object(plugin, "do_unfollow", return_value=True), \
             patch("InstaAddict.plugins.action_unfollow_followers.random_sleep"):
            try:
                plugin.iterate_over_followings(
                    device=mock_device,
                    count=1,
                    on_unfollow=MagicMock(),
                    storage=mock_storage,
                    unfollow_restriction=UnfollowRestriction.ANY,
                    my_username="testuser",
                    posts_end_detector=MagicMock(),
                    job_name="unfollow-any",
                )
            except Exception as e:
                self.fail(f"iterate_over_followings failed with exception: {e}")

        # Heartbeat was called for iterating visible followings
        self.assertTrue(any(c[0][0] == "unfollow-followers" for c in mock_heartbeat.call_args_list))


if __name__ == "__main__":
    unittest.main()

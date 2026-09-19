import unittest
from unittest.mock import MagicMock, patch
from InstaAddict.core.handle_sources import handle_posts


class TestPostViewCommenting(unittest.TestCase):
    """Unit tests for post-view commenting in handle_posts (Route-059)."""

    def setUp(self):
        self.mock_plugin = MagicMock()
        self.mock_plugin.args = MagicMock()
        self.mock_plugin.args.comment_percentage = "100"
        self.mock_plugin.args.truncate_sources = None
        self.mock_plugin.args.can_reinteract_after = "0"
        self.mock_plugin.args.scrape_to_file = None
        self.mock_plugin.args.feed = "1"
        self.mock_plugin.args.skipped_posts_limit = 5
        self.mock_plugin.current_mode = "feed"

        self.mock_device = MagicMock()
        self.mock_device.device_id = "test-device"
        self.mock_device.app_id = "com.instagram.android"
        self.mock_device.find.return_value.exists.return_value = False

        self.mock_session_state = MagicMock()
        self.mock_session_state.id = "test-session"
        self.mock_session_state.my_username = "test_user"
        self.mock_session_state.totalLikes = 0
        self.mock_session_state.totalComments = 0
        self.mock_session_state.check_limit.return_value = False
        self.mock_session_state.Limit = MagicMock()
        self.mock_session_state.Limit.LIKES = "likes"
        self.mock_session_state.Limit.COMMENTS = "comments"
        self.mock_session_state.Limit.SUCCESS = "success"
        self.mock_session_state.Limit.TOTAL = "total"

        self.mock_storage = MagicMock()
        self.mock_storage.is_user_in_blacklist.return_value = False
        self.mock_storage.check_user_was_interacted.return_value = (False, None)

        self.mock_filter = MagicMock()
        self.mock_filter.is_num_likers_in_range.return_value = True
        self.mock_filter.can_comment.return_value = (True, True, True, True)

        self.mock_on_interaction = MagicMock(return_value=True)
        self.mock_interaction = MagicMock(return_value=(True, False, False, False, False, 1, 0, 0))

    def _setup_views(self, mock_posts_view, mock_opened_view):
        post_view_inst = MagicMock()
        post_view_inst._check_if_last_post.return_value = (
            False, "cool dog description", "cool_dog", False, False, False
        )
        post_view_inst._find_likers_container.return_value = (True, 10)
        post_view_inst._get_owner_name.return_value = "cool_dog"
        post_view_inst._check_if_liked.return_value = True
        mock_posts_view.return_value = post_view_inst

        opened_view_inst = MagicMock()
        opened_view_inst._is_post_liked.return_value = (False, MagicMock())
        opened_view_inst.detect_opened_media_type.return_value = "photo"
        mock_opened_view.return_value = opened_view_inst

        return post_view_inst, opened_view_inst

    @patch("InstaAddict.core.handle_sources.nav_to_feed")
    @patch("InstaAddict.core.handle_sources.PostsViewList")
    @patch("InstaAddict.core.handle_sources.OpenedPostView")
    @patch("InstaAddict.core.handle_sources.TabBarView")
    @patch("InstaAddict.core.interaction._comment")
    @patch("InstaAddict.core.handle_sources.get_value")
    def test_feed_post_comments_when_probability_triggers(
        self, mock_get_value, mock_comment, mock_tab_bar, mock_opened_view, mock_posts_view, mock_nav_feed
    ):
        mock_get_value.side_effect = (
            lambda val, *args, **kwargs: 1 if "feed" in str(args) else (100 if val == "100" else 1)
        )

        def fake_comment(*args, **kwargs):
            session = kwargs.get("session_state")
            if session:
                session.totalComments += 1
            return True

        mock_comment.side_effect = fake_comment
        self._setup_views(mock_posts_view, mock_opened_view)

        handle_posts(
            self.mock_plugin,
            self.mock_device,
            self.mock_session_state,
            "Own Feed",
            "feed",
            self.mock_storage,
            self.mock_filter,
            self.mock_on_interaction,
            self.mock_interaction,
            None,
            100,
            None,
        )

        mock_comment.assert_called_once()
        self.assertEqual(self.mock_session_state.totalComments, 1)
        self.assertEqual(self.mock_session_state.totalLikes, 1)

    @patch("InstaAddict.core.handle_sources.nav_to_feed")
    @patch("InstaAddict.core.handle_sources.PostsViewList")
    @patch("InstaAddict.core.handle_sources.OpenedPostView")
    @patch("InstaAddict.core.handle_sources.TabBarView")
    @patch("InstaAddict.core.interaction._comment")
    @patch("InstaAddict.core.handle_sources.get_value")
    def test_comment_skipped_when_comment_limit_reached(
        self, mock_get_value, mock_comment, mock_tab_bar, mock_opened_view, mock_posts_view, mock_nav_feed
    ):
        mock_get_value.side_effect = (
            lambda val, *args, **kwargs: 1 if "feed" in str(args) else (100 if val == "100" else 1)
        )

        def check_limit_side_effect(limit_type=None, output=False):
            if limit_type == "comments":
                return True
            return False

        self.mock_session_state.check_limit.side_effect = check_limit_side_effect
        self._setup_views(mock_posts_view, mock_opened_view)

        handle_posts(
            self.mock_plugin,
            self.mock_device,
            self.mock_session_state,
            "Own Feed",
            "feed",
            self.mock_storage,
            self.mock_filter,
            self.mock_on_interaction,
            self.mock_interaction,
            None,
            100,
            None,
        )

        mock_comment.assert_not_called()
        self.assertEqual(self.mock_session_state.totalComments, 0)

    @patch("InstaAddict.core.handle_sources.nav_to_feed")
    @patch("InstaAddict.core.handle_sources.PostsViewList")
    @patch("InstaAddict.core.handle_sources.OpenedPostView")
    @patch("InstaAddict.core.handle_sources.TabBarView")
    @patch("InstaAddict.core.interaction._comment")
    @patch("InstaAddict.core.handle_sources.get_value")
    def test_comment_skipped_when_filter_disallows_mode(
        self, mock_get_value, mock_comment, mock_tab_bar, mock_opened_view, mock_posts_view, mock_nav_feed
    ):
        mock_get_value.side_effect = (
            lambda val, *args, **kwargs: 1 if "feed" in str(args) else (100 if val == "100" else 1)
        )
        self.mock_filter.can_comment.return_value = (True, True, True, False)
        self._setup_views(mock_posts_view, mock_opened_view)

        handle_posts(
            self.mock_plugin,
            self.mock_device,
            self.mock_session_state,
            "Own Feed",
            "feed",
            self.mock_storage,
            self.mock_filter,
            self.mock_on_interaction,
            self.mock_interaction,
            None,
            100,
            None,
        )

        mock_comment.assert_not_called()
        self.assertEqual(self.mock_session_state.totalComments, 0)

    @patch("InstaAddict.core.handle_sources.nav_to_feed")
    @patch("InstaAddict.core.handle_sources.PostsViewList")
    @patch("InstaAddict.core.handle_sources.OpenedPostView")
    @patch("InstaAddict.core.handle_sources.TabBarView")
    @patch("InstaAddict.core.interaction._comment")
    @patch("InstaAddict.core.handle_sources.get_value")
    def test_comment_exception_handled_gracefully(
        self, mock_get_value, mock_comment, mock_tab_bar, mock_opened_view, mock_posts_view, mock_nav_feed
    ):
        mock_get_value.side_effect = (
            lambda val, *args, **kwargs: 1 if "feed" in str(args) else (100 if val == "100" else 1)
        )
        mock_comment.side_effect = RuntimeError("Simulated UI error in comment box")
        self._setup_views(mock_posts_view, mock_opened_view)

        handle_posts(
            self.mock_plugin,
            self.mock_device,
            self.mock_session_state,
            "Own Feed",
            "feed",
            self.mock_storage,
            self.mock_filter,
            self.mock_on_interaction,
            self.mock_interaction,
            None,
            100,
            None,
        )

        self.assertEqual(self.mock_session_state.totalLikes, 1)
        self.assertEqual(self.mock_session_state.totalComments, 0)


if __name__ == "__main__":
    unittest.main()

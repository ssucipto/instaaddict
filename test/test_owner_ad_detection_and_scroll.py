import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from InstaAddict.core.views import (
    PostsViewList,
    OpenedPostView,
    Owner,
    SwipeTo,
    load_config,
)
import InstaAddict.core.views as views


class TestOwnerAdDetectionAndScroll(unittest.TestCase):
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
        self.res = views.ResourceID

    def test_post_owner_missing_returns_is_ad_false(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        mock_elem = MagicMock()
        mock_elem.exists.return_value = False
        device.find.return_value = mock_elem

        with patch("InstaAddict.core.views.UniversalActions._swipe_points"):
            username, is_ad, is_hashtag = post_view._post_owner(
                "hashtag-posts-recent", Owner.GET_NAME
            )

        self.assertFalse(username)
        self.assertFalse(is_ad, "Missing owner name must never be flagged as an ad!")
        self.assertFalse(is_hashtag)

    def test_post_owner_resolves_clips_author_username(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        feed_name = MagicMock(exists=MagicMock(return_value=False))

        clips_user = MagicMock()
        clips_user.exists.return_value = True
        clips_user.get_text.return_value = "happyfitangie✨  "
        clips_user.get_desc.return_value = "happyfitangie✨"
        clips_user.get_bounds.return_value = {"top": 1900, "bottom": 2000}

        sibling_obj = MagicMock(exists=MagicMock(return_value=False))
        clips_user.sibling.return_value = sibling_obj

        not_found = MagicMock(exists=MagicMock(return_value=False))

        def mock_find(**kwargs):
            res_id = kwargs.get("resourceIdMatches", "")
            if res_id == self.res.ROW_FEED_PHOTO_PROFILE_NAME:
                return feed_name
            if res_id == self.res.CLIPS_AUTHOR_USERNAME:
                return clips_user
            return not_found

        device.find.side_effect = mock_find

        username, is_ad, is_hashtag = post_view._post_owner(
            "hashtag-posts-recent", Owner.GET_NAME
        )

        self.assertEqual(username, "happyfitangie")
        self.assertFalse(is_ad)
        self.assertFalse(is_hashtag)

    def test_post_owner_resolves_clips_author_profile_pic_desc(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        feed_name = MagicMock(exists=MagicMock(return_value=False))
        clips_user = MagicMock(exists=MagicMock(return_value=False))

        clips_pic = MagicMock()
        clips_pic.exists.return_value = True
        clips_pic.get_text.return_value = ""
        clips_pic.get_desc.return_value = "Profile picture of phoenix_di"
        clips_pic.get_bounds.return_value = {"top": 1900, "bottom": 2000}

        sibling_obj = MagicMock(exists=MagicMock(return_value=False))
        clips_pic.sibling.return_value = sibling_obj

        not_found = MagicMock(exists=MagicMock(return_value=False))

        def mock_find(**kwargs):
            res_id = kwargs.get("resourceIdMatches", "")
            if res_id == self.res.ROW_FEED_PHOTO_PROFILE_NAME:
                return feed_name
            if res_id == self.res.CLIPS_AUTHOR_USERNAME:
                return clips_user
            if res_id == self.res.CLIPS_AUTHOR_PROFILE_PIC:
                return clips_pic
            return not_found

        device.find.side_effect = mock_find

        username, is_ad, is_hashtag = post_view._post_owner(
            "hashtag-posts-recent", Owner.GET_NAME
        )

        self.assertEqual(username, "phoenix_di")
        self.assertFalse(is_ad)

    def test_post_owner_resolves_feed_photo_profile_name(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        feed_name = MagicMock()
        feed_name.exists.return_value = True
        feed_name.get_text.return_value = "therusselbunch • Follow"
        feed_name.get_desc.return_value = None
        feed_name.get_bounds.return_value = {"top": 300, "bottom": 380}

        sibling_obj = MagicMock(exists=MagicMock(return_value=False))
        feed_name.sibling.return_value = sibling_obj

        not_found = MagicMock(exists=MagicMock(return_value=False))

        def mock_find(**kwargs):
            res_id = kwargs.get("resourceIdMatches", "")
            if res_id == self.res.ROW_FEED_PHOTO_PROFILE_NAME:
                return feed_name
            return not_found

        device.find.side_effect = mock_find

        username, is_ad, is_hashtag = post_view._post_owner(
            "hashtag-posts-recent", Owner.GET_NAME
        )

        self.assertEqual(username, "therusselbunch")
        self.assertFalse(is_ad)

    def test_post_owner_open_clicks_clips_author(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        feed_name = MagicMock(exists=MagicMock(return_value=False))

        clips_user = MagicMock()
        clips_user.exists.return_value = True
        clips_user.get_text.return_value = "happyfitangie"
        clips_user.get_desc.return_value = "happyfitangie"
        clips_user.get_bounds.return_value = {"top": 1900, "bottom": 2000}

        sibling_obj = MagicMock(exists=MagicMock(return_value=False))
        clips_user.sibling.return_value = sibling_obj

        not_found = MagicMock(exists=MagicMock(return_value=False))

        def mock_find(**kwargs):
            res_id = kwargs.get("resourceIdMatches", "")
            if res_id == self.res.ROW_FEED_PHOTO_PROFILE_NAME:
                return feed_name
            if res_id == self.res.CLIPS_AUTHOR_USERNAME:
                return clips_user
            return not_found

        device.find.side_effect = mock_find

        with patch.object(
            post_view, "_if_action_bar_is_over_obj_swipe"
        ):
            opened, is_ad, is_hashtag = post_view._post_owner(
                "hashtag-posts-recent", Owner.OPEN
            )

        self.assertTrue(opened)
        self.assertFalse(is_ad)
        clips_user.click.assert_called_once()

    def test_check_if_last_post_extracts_clips_caption(self):
        device = MagicMock()
        post_view = PostsViewList(device)

        clips_caption = MagicMock()
        clips_caption.exists.return_value = True
        clips_caption.get_desc.return_value = "Me and my best part #doglife #puppy"
        clips_caption.get_text.return_value = ""

        not_found = MagicMock(exists=MagicMock(return_value=False))

        def mock_find(**kwargs):
            res_id = kwargs.get("resourceIdMatches", "")
            if res_id == self.res.CLIPS_CAPTION_COMPONENT:
                return clips_caption
            return not_found

        device.find.side_effect = mock_find

        with patch.object(
            post_view, "_post_owner", return_value=("phoenix_di", False, False)
        ), patch.object(post_view, "_has_tags", return_value=False):
            is_same, desc, author, is_ad, is_hashtag, has_tags = (
                post_view._check_if_last_post(
                    "PREV_CAPTION", "hashtag-posts-recent"
                )
            )

        self.assertFalse(is_same)
        self.assertEqual(author, "phoenix_di")
        self.assertFalse(is_ad)
        self.assertIn("ME AND MY BEST PART", desc)

    def test_swipe_to_fit_posts_reels_mode_single_fluid_swipe(self):
        device = MagicMock()
        device.get_info.return_value = {
            "displayWidth": 1080,
            "displayHeight": 2400,
        }
        post_view = PostsViewList(device)

        clips_viewer = MagicMock()
        clips_viewer.exists.return_value = True
        device.find.return_value = clips_viewer

        res = post_view.swipe_to_fit_posts(SwipeTo.NEXT_POST)

        self.assertTrue(res)
        device.swipe_points.assert_called_once_with(
            540.0,
            1920,
            540.0,
            480,
        )

    def test_swipe_to_fit_posts_feed_mode_no_gap_retry_loop(self):
        device = MagicMock()
        device.get_info.return_value = {
            "displayWidth": 1080,
            "displayHeight": 2400,
        }
        post_view = PostsViewList(device)

        mock_not_found = MagicMock()
        mock_not_found.exists.return_value = False
        device.find.return_value = mock_not_found

        with patch.object(
            post_view, "_get_current_media_bounds", return_value={"top": 300, "bottom": 1800}
        ), patch.object(
            post_view, "_get_action_bar_position", return_value=(True, 0, 150)
        ), patch.object(
            post_view, "swipe_to_fit_posts", wraps=post_view.swipe_to_fit_posts
        ) as spy_swipe:
            res = post_view.swipe_to_fit_posts(SwipeTo.NEXT_POST)

        self.assertTrue(res)
        self.assertEqual(spy_swipe.call_count, 1)
        device.swipe_points.assert_called_once()

    def test_opened_post_view_likes_reels_via_like_button(self):
        device = MagicMock()
        opened_view = OpenedPostView(device)

        media_container = MagicMock(exists=MagicMock(return_value=False))

        like_button = MagicMock()
        like_button.exists.return_value = True
        like_button.get_selected.return_value = True

        def mock_find(**kwargs):
            res_id = kwargs.get("resourceIdMatches", "")
            if self.res.MEDIA_CONTAINER in res_id:
                return media_container
            return like_button

        device.find.side_effect = mock_find

        with patch("InstaAddict.core.views.UniversalActions.detect_block"):
            liked = opened_view.like_post()

        self.assertTrue(liked)
        like_button.click.assert_called_once()


if __name__ == "__main__":
    unittest.main()

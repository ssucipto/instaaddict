from unittest.mock import MagicMock, patch

import InstaAddict.core.views as views
import InstaAddict.core.interaction as interaction
from InstaAddict.core.resources import ResourceID as resources
from InstaAddict.core.views import FollowStatus, MediaType, ProfileView, Direction
from InstaAddict.core.interaction import _follow, _comment, load_random_comment
from InstaAddict.plugins.action_unfollow_followers import ActionUnfollowFollowers

# Ensure resources are initialized for testing
views.ResourceID = resources("com.instagram.android")
interaction.ResourceID = resources("com.instagram.android")


class TestFollowButtonDetection:
    """Test getFollowButton against modern Instagram v446+ layouts."""

    def test_follow_button_with_non_clickable_textview(self):
        device = MagicMock()
        text_view = MagicMock()
        text_view.exists.return_value = True
        text_view.get_text.return_value = "Follow"
        text_view.get_property.return_value = "Follow"

        # Simulating modern IG: device.find without clickable=True matches the TextView
        device.find.return_value = text_view

        profile_view = ProfileView(device)
        btn, status = profile_view.getFollowButton()

        assert btn is text_view
        assert status == FollowStatus.FOLLOW

    def test_following_button_detection(self):
        device = MagicMock()
        text_view = MagicMock()
        text_view.exists.return_value = True
        text_view.get_text.return_value = "Following"

        device.find.return_value = text_view

        profile_view = ProfileView(device)
        btn, status = profile_view.getFollowButton()

        assert btn is text_view
        assert status == FollowStatus.FOLLOWING

    def test_follow_back_button_detection(self):
        device = MagicMock()
        text_view = MagicMock()
        text_view.exists.return_value = True
        text_view.get_text.return_value = "Follow Back"

        device.find.return_value = text_view

        profile_view = ProfileView(device)
        btn, status = profile_view.getFollowButton()

        assert btn is text_view
        assert status == FollowStatus.FOLLOW_BACK

    def test_follow_button_via_content_description_fallback(self):
        device = MagicMock()
        # First lookup (text) does not exist
        missing_text = MagicMock()
        missing_text.exists.return_value = False

        # Fallback 1 (description) exists
        desc_view = MagicMock()
        desc_view.exists.return_value = True
        desc_view.get_text.return_value = ""
        desc_view.get_property.return_value = "Follow"

        device.find.side_effect = [
            MagicMock(),  # action_bar
            missing_text,
            desc_view
        ]

        profile_view = ProfileView(device)
        btn, status = profile_view.getFollowButton()

        assert btn is desc_view
        assert status == FollowStatus.FOLLOW

    def test_follow_button_via_resource_id_fallback(self):
        device = MagicMock()
        missing_text = MagicMock()
        missing_text.exists.return_value = False
        missing_desc = MagicMock()
        missing_desc.exists.return_value = False

        res_view = MagicMock()
        res_view.exists.return_value = True
        res_view.get_text.return_value = "Follow"

        device.find.side_effect = [
            MagicMock(),  # action_bar
            missing_text,
            missing_desc,
            res_view
        ]

        profile_view = ProfileView(device)
        btn, status = profile_view.getFollowButton()

        assert btn is res_view
        assert status == FollowStatus.FOLLOW

    def test_follow_button_nonexistent_returns_none_status(self):
        device = MagicMock()
        missing = MagicMock()
        missing.exists.return_value = False
        device.find.return_value = missing

        profile_view = ProfileView(device)
        btn, status = profile_view.getFollowButton()

        assert btn is None
        assert status == FollowStatus.NONE


class TestNavigateToFollowing:
    """Test ProfileView.navigateToFollowing return behaviors."""

    def test_navigate_to_following_with_tab(self):
        device = MagicMock()
        following_btn = MagicMock()
        following_btn.exists.return_value = True
        tab_layout = MagicMock()
        following_tab = MagicMock()
        following_tab.exists.return_value = True
        following_tab.get_property.return_value = False
        tab_layout.child.return_value = following_tab

        device.find.side_effect = lambda **kwargs: (
            following_btn if "resourceIdMatches" in kwargs and "following" in str(kwargs["resourceIdMatches"]).lower()
            else tab_layout
        )

        profile_view = ProfileView(device)
        result = profile_view.navigateToFollowing()

        assert result is True
        following_btn.click_retry.assert_called_once()
        following_tab.click.assert_called_once()

    def test_navigate_to_following_direct_list_fallback(self):
        device = MagicMock()
        following_btn = MagicMock()
        following_btn.exists.return_value = True

        tab_layout = MagicMock()
        missing_tab = MagicMock()
        missing_tab.exists.return_value = False
        tab_layout.child.return_value = missing_tab

        following_list = MagicMock()
        following_list.exists.return_value = True

        def find_mock(**kwargs):
            res = str(kwargs.get("resourceIdMatches", ""))
            if "row_profile_header_following_container" in res or "profile_header" in res:
                return following_btn
            if "unified_follow_list_tab_layout" in res:
                return tab_layout
            if "follow_list" in res or "recycler" in res:
                return following_list
            obj = MagicMock()
            obj.exists.return_value = True
            return obj

        device.find.side_effect = find_mock

        profile_view = ProfileView(device)
        result = profile_view.navigateToFollowing()

        assert result is True


class TestCommentPipeline:
    """Test _comment and load_random_comment resilience."""

    def test_comment_reels_does_not_swipe_down(self):
        device = MagicMock()
        session_state = MagicMock()
        session_state.check_limit.return_value = False
        session_state.totalComments = 0
        args = MagicMock()
        args.dont_type = True

        comment_btn = MagicMock()
        comment_btn.exists.return_value = True

        comment_box = MagicMock()
        comment_box.exists.return_value = True
        comment_box.get_text.return_value = ""

        post_btn = MagicMock()
        post_btn.exists.return_value = True

        blocked_dialog = MagicMock()
        blocked_dialog.exists.return_value = False

        posted_text = MagicMock()
        posted_text.exists.return_value = True

        def find_mock(**kwargs):
            if "resourceIdMatches" in kwargs or "resourceId" in kwargs:
                res = str(kwargs.get("resourceIdMatches") or kwargs.get("resourceId"))
                if "comment_button" in res or "row_feed_button_comment" in res:
                    return comment_btn
                if "layout_comment_thread_edittext" in res:
                    return comment_box
                if "post_button" in res:
                    return post_btn
            if "textMatches" in kwargs:
                return blocked_dialog
            if "descriptionMatches" in kwargs or "description" in kwargs:
                return posted_text
            obj = MagicMock()
            obj.exists.return_value = True
            return obj

        device.find.side_effect = find_mock

        with patch("InstaAddict.core.interaction.UniversalActions") as mock_ua, \
             patch("InstaAddict.core.interaction.random_choice", return_value=True), \
             patch("subprocess.run"):
            ua_instance = mock_ua.return_value

            success = _comment(
                device,
                my_username="test_user",
                comment_percentage=100,
                args=args,
                session_state=session_state,
                media_type=MediaType.REEL,
                explicit_comment="Great Reel! :fire:",
            )

            # Swipe DOWN must NOT be called for Reels!
            for call in ua_instance._swipe_points.call_args_list:
                assert call.kwargs.get("direction") != Direction.DOWN

            assert success is True
            assert session_state.totalComments == 1

    def test_load_random_comment_non_sectioned_file(self):
        with patch("InstaAddict.core.interaction._load_and_clean_txt_file", return_value=["Nice picture!", "Great shot!"]):
            comment = load_random_comment("test_user", MediaType.PHOTO)
            assert comment in ["Nice picture!", "Great shot!"]

    def test_load_random_comment_missing_file_fallback(self):
        with patch("InstaAddict.core.interaction._load_and_clean_txt_file", return_value=None):
            comment = load_random_comment("test_user", MediaType.REEL)
            assert comment is not None
            assert len(comment) > 0


class TestFollowAndUnfollowActions:
    """Test _follow and action_unfollow_followers without clickable=True constraints."""

    def test_follow_action_without_clickable_constraint(self):
        device = MagicMock()
        session_state = MagicMock()
        session_state.check_limit.return_value = False

        follow_btn = MagicMock()
        follow_btn.exists.return_value = True

        unfollow_btn = MagicMock()
        unfollow_btn.exists.return_value = False

        followback_btn = MagicMock()
        followback_btn.exists.return_value = False

        coordinator = MagicMock()
        coordinator.exists.return_value = False

        unfollow_after_click = MagicMock()
        unfollow_after_click.exists.return_value = True

        call_count = 0
        def find_mock(**kwargs):
            nonlocal call_count
            text_match = str(kwargs.get("textMatches", ""))
            if "Follow$" in text_match:
                return follow_btn
            if "Following|^Requested" in text_match:
                call_count += 1
                return unfollow_after_click if call_count > 1 else unfollow_btn
            if "Follow Back" in text_match:
                return followback_btn
            if "coordinator" in str(kwargs.get("resourceId", "")):
                return coordinator
            obj = MagicMock()
            obj.exists.return_value = False
            return obj

        device.find.side_effect = find_mock

        with patch("InstaAddict.core.interaction.UniversalActions"):
            result = _follow(
                device,
                username="test_target",
                follow_percentage=100,
                args=MagicMock(),
                session_state=session_state,
                swipe_amount=0,
            )

            assert result is True
            follow_btn.click.assert_called_once()

    def test_unfollow_dialog_confirmation_fallback(self):
        device = MagicMock()
        unfollow_btn = MagicMock()
        unfollow_btn.exists.return_value = True

        confirm_btn = MagicMock()
        confirm_btn.exists.return_value = True

        private_btn = MagicMock()
        private_btn.exists.return_value = False

        def find_mock(**kwargs):
            if "textMatches" in kwargs and "Unfollow" in str(kwargs["textMatches"]):
                return confirm_btn
            if "resourceId" in kwargs and "follow_sheet_unfollow_row" in str(kwargs["resourceId"]):
                missing = MagicMock()
                missing.exists.return_value = False
                return missing
            obj = MagicMock()
            obj.exists.return_value = True
            return obj

        device.find.side_effect = find_mock

        plugin = ActionUnfollowFollowers()
        plugin.ResourceID = resources("com.instagram.android")
        with patch.object(plugin, "check_is_follower", return_value=False), \
             patch("InstaAddict.plugins.action_unfollow_followers.UniversalActions.detect_block"):
            res = plugin.do_unfollow(
                device,
                username="unfollow_target",
                my_username="my_user",
                check_if_is_follower=False,
                unfollow_followers=False,
            )
            assert res is True
            device.back.assert_called()

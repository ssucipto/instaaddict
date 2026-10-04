import os
from unittest.mock import MagicMock, patch, call
import pytest
from uiautomator2 import UiObjectNotFoundError

from InstaAddict.core.dogfood import DogfoodOptimizer
from InstaAddict.core.views import TabBarView, ProfileView, HashTagView, PlacesView
from InstaAddict.plugins.action_unfollow_followers import ActionUnfollowFollowers, UnfollowRestriction
from InstaAddict.core.resources import ResourceID as resources
from InstaAddict.plugins.interact_hashtag_posts import InteractHashtagPosts
from InstaAddict.core.navigation import nav_to_blogger, nav_to_hashtag_or_place
from InstaAddict.core.storage import FollowingStatus


def test_dogfood_optimizer_cooldown_recommendation_12h(tmp_path):
    """Verify DogfoodOptimizer recommends 12h when current cooldown <= 24h and skips are high."""
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("can-reinteract-after: '24'\n", encoding="utf-8")

    optimizer = DogfoodOptimizer(username="testuser")
    optimizer.config_path = str(cfg_file)

    session_data = {
        "total_interactions": 50,
        "successful_interactions": 10,
        "total_likes": 8,
        "total_followed": 2,
        "total_crashes": 0,
        "total_subscreen_escapes": 0,
        "skip_reasons": {"COOLDOWN": 30, "WHITELIST": 10},
    }

    dummy_diag = {
        "total_errors": 0,
        "total_warnings": 0,
        "top_signatures": [],
        "quota_429_errors": 0,
        "fatal_crashes": 0,
    }

    with patch.object(optimizer, "_load_sessions", return_value=[session_data]), \
         patch.object(optimizer, "_analyze_error_log", return_value=dummy_diag), \
         patch.object(optimizer, "_save_suggestions"):
        report = optimizer.analyze()
        recs = report.get("recommendations", [])
        cooldown_recs = [r for r in recs if r.get("parameter") == "can-reinteract-after"]
        assert len(cooldown_recs) == 1
        assert cooldown_recs[0]["suggested_value"] == "12"
        assert "12h" in cooldown_recs[0]["action"]


def test_dogfood_optimizer_cooldown_recommendation_24h(tmp_path):
    """Verify DogfoodOptimizer recommends 24h when current cooldown > 24h."""
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text("can-reinteract-after: '48'\n", encoding="utf-8")

    optimizer = DogfoodOptimizer(username="testuser")
    optimizer.config_path = str(cfg_file)

    session_data = {
        "total_interactions": 50,
        "successful_interactions": 10,
        "total_likes": 8,
        "total_followed": 2,
        "total_crashes": 0,
        "total_subscreen_escapes": 0,
        "skip_reasons": {"COOLDOWN": 30, "WHITELIST": 10},
    }

    dummy_diag = {
        "total_errors": 0,
        "total_warnings": 0,
        "top_signatures": [],
        "quota_429_errors": 0,
        "fatal_crashes": 0,
    }

    with patch.object(optimizer, "_load_sessions", return_value=[session_data]), \
         patch.object(optimizer, "_analyze_error_log", return_value=dummy_diag), \
         patch.object(optimizer, "_save_suggestions"):
        report = optimizer.analyze()
        recs = report.get("recommendations", [])
        cooldown_recs = [r for r in recs if r.get("parameter") == "can-reinteract-after"]
        assert len(cooldown_recs) == 1
        assert cooldown_recs[0]["suggested_value"] == "24"


def test_tab_bar_view_escape_subscreens_launcher_restore():
    """Verify TabBarView._escape_subscreens detects background launcher and restores Instagram."""
    mock_device = MagicMock()
    is_opened_calls = [False, True, True, True, True]
    mock_device._ig_is_opened.side_effect = lambda: is_opened_calls.pop(0) if is_opened_calls else True

    tab_bar = TabBarView(mock_device)
    # is_tab_bar_visible returns False on first check, True on second
    with patch.object(tab_bar, "is_tab_bar_visible", side_effect=[False, True]), \
         patch("InstaAddict.core.utils.open_instagram") as mock_open_ig, \
         patch("InstaAddict.core.views.random_sleep"):

        res = tab_bar._escape_subscreens(max_attempts=3)
        assert res is True
        mock_open_ig.assert_called_once_with(mock_device)


def test_profile_view_navigate_to_followers_progressive_polling():
    """Verify ProfileView.navigateToFollowers polls multiple times to tolerate slow loads."""
    mock_device = MagicMock()
    mock_btn = MagicMock()
    # Button does not exist on first attempt, then exists
    exists_calls = [False, False, False, True, True, True, True, True, True, True]
    mock_btn.exists.side_effect = lambda *a, **k: exists_calls.pop(0) if exists_calls else True
    mock_device.find.return_value = mock_btn

    profile_view = ProfileView(mock_device)

    with patch("InstaAddict.core.views.random_sleep"), \
         patch("InstaAddict.core.watchdog.record_heartbeat") as mock_hb:
        res = profile_view.navigateToFollowers()
        assert res is True
        assert mock_btn.click.called
        assert mock_hb.called


def test_profile_view_navigate_to_followers_failure_no_throw():
    """Verify ProfileView.navigateToFollowers returns False cleanly if button never appears."""
    mock_device = MagicMock()
    mock_btn = MagicMock()
    mock_btn.exists.return_value = False
    mock_device.find.return_value = mock_btn

    profile_view = ProfileView(mock_device)

    with patch("InstaAddict.core.views.random_sleep"):
        res = profile_view.navigateToFollowers()
        assert res is False


def test_action_unfollow_non_bot_saturation_break():
    """Verify ActionUnfollowFollowers terminates early when 30 consecutive non-bot accounts are found."""
    mock_device = MagicMock()
    mock_device.get_info.return_value = {"displayWidth": 1080, "displayHeight": 2400}
    plugin = ActionUnfollowFollowers()
    plugin.args = MagicMock()
    plugin.args.app_id = "com.instagram.android"
    plugin.args.unfollow_delay = "3"
    plugin.args.ignore_followers_cache = False
    plugin.ResourceID = resources(plugin.args.app_id)
    plugin.session_state = MagicMock()
    plugin.session_state.check_limit.return_value = False

    mock_storage = MagicMock()
    mock_storage.non_bot_followings = set()
    mock_storage.is_user_in_whitelist.return_value = False
    mock_storage.is_follower.return_value = False
    mock_storage.is_non_bot_following.return_value = False
    # All users are NOT_IN_LIST (not followed by bot)
    mock_storage.get_following_status.return_value = FollowingStatus.NOT_IN_LIST
    mock_storage.check_user_was_interacted.return_value = (False, None)

    # 35 mock user rows
    items = []
    for i in range(35):
        row = MagicMock()
        row.get_height.return_value = 50
        name_view = MagicMock()
        name_view.exists.return_value = True
        name_view.get_text.return_value = f"user_{i}"
        row.child.return_value = name_view
        items.append(row)

    mock_user_list = MagicMock()
    mock_user_list.__iter__.return_value = iter(items)
    mock_device.find.return_value = mock_user_list

    mock_detector = MagicMock()

    with patch("InstaAddict.plugins.action_unfollow_followers.inspect_current_view", return_value=(50, 35)), \
         patch("InstaAddict.core.views.UniversalActions._swipe_points"), \
         patch("InstaAddict.core.watchdog.record_heartbeat"):

        plugin.iterate_over_followings(
            mock_device,
            count=10,
            on_unfollow=MagicMock(),
            storage=mock_storage,
            unfollow_restriction=UnfollowRestriction.FOLLOWED_BY_SCRIPT,
            my_username="me",
            job_name="unfollow-non-followers",
            posts_end_detector=mock_detector,
        )

        assert mock_storage.save_non_bot_followings.called
        # Should have stopped at 30 items without processing all 35
        assert mock_storage.add_non_bot_following.call_count == 30


def test_hashtag_recent_tab_locators():
    """Verify HashTagView and PlacesView _getRecentTab locators search modern variants."""
    mock_device = MagicMock()
    mock_tab = MagicMock()
    mock_tab.exists.return_value = True
    mock_device.find.return_value = mock_tab

    ht_view = HashTagView(mock_device)
    tab = ht_view._getRecentTab()
    assert tab.exists()

    pl_view = PlacesView(mock_device)
    tab_pl = pl_view._getRecentTab()
    assert tab_pl.exists()


def test_nav_to_blogger_checks_navigation_success():
    """Verify nav_to_blogger returns False if navigateToFollowers fails."""
    mock_device = MagicMock()

    with patch("InstaAddict.core.navigation.TabBarView") as mock_tb, \
         patch("InstaAddict.core.navigation.ProfileView") as mock_pv:
        mock_search = MagicMock()
        mock_search.navigate_to_target.return_value = True
        mock_tb.return_value.navigateToSearch.return_value = mock_search

        profile_view_inst = MagicMock()
        profile_view_inst.navigateToFollowers.return_value = False
        mock_pv.return_value = profile_view_inst

        res = nav_to_blogger(mock_device, "targetuser", "blogger-followers")
        assert res is False


def test_interact_hashtag_posts_attempt_cap():
    """Verify InteractHashtagPosts caps retries at 2 attempts on persistent job failure."""
    plugin = InteractHashtagPosts()
    plugin.session_state = MagicMock()
    plugin.session_state.check_limit.return_value = (False, False, False)
    plugin.args = MagicMock()
    plugin.args.device = "mock"
    plugin.args.screen_record = False
    plugin.args.truncate_sources = "1-2"
    plugin.args.hashtag_posts_recent = ["testtag"]

    mock_configs = MagicMock()
    mock_configs.args = plugin.args
    mock_device = MagicMock()

    call_count = 0
    def failing_handle_hashtag(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise IndexError("list index out of range")

    plugin.handle_hashtag = failing_handle_hashtag

    with patch("InstaAddict.core.hashtag_manager.HashtagManager.get_instance") as mock_hm, \
         patch("InstaAddict.core.decorators.restart"):
        mock_hm.return_value.has_tiered_sources.return_value = False
        # Running run() should not loop indefinitely; should stop after 2 attempts
        plugin.run(
            mock_device,
            mock_configs,
            MagicMock(),
            [plugin.session_state],
            MagicMock(),
            "hashtag-posts-recent",
        )
        assert call_count == 2

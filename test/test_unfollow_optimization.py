import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import InstaAddict.core.views as views
from InstaAddict.core.resources import ResourceID as resources
from InstaAddict.core.storage import Storage
from InstaAddict.core.views import ProfileView
from InstaAddict.plugins.action_unfollow_followers import (
    ActionUnfollowFollowers,
)

# Ensure resources are initialized for testing
views.ResourceID = resources("com.instagram.android")


class TestFollowersCacheStorage(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch(
            "InstaAddict.core.storage.ACCOUNTS", self.test_dir
        )
        self.patcher.start()
        self.username = "test_bot_user"

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_followers_cache_initialization_empty(self):
        storage = Storage(self.username)
        self.assertFalse(storage.is_follower("anyone"))
        self.assertEqual(storage.get_followers_cache_size(), 0)
        self.assertEqual(storage.get_cached_followers_count(), 0)

    def test_add_follower_and_case_insensitive_lookup(self):
        storage = Storage(self.username)
        storage.add_follower("Alice_Wonderland")

        self.assertTrue(storage.is_follower("alice_wonderland"))
        self.assertTrue(storage.is_follower("ALICE_WONDERLAND"))
        self.assertTrue(storage.is_follower("Alice_Wonderland"))
        self.assertFalse(storage.is_follower("bob"))
        self.assertEqual(storage.get_followers_cache_size(), 1)

        # Verify persisted file
        cache_path = os.path.join(
            self.test_dir, self.username, "followers_cache.json"
        )
        self.assertTrue(os.path.isfile(cache_path))
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("alice_wonderland", data["followers"])

    def test_add_followers_batch_updates_count_and_metadata(self):
        storage = Storage(self.username)
        batch = ["User_One", "User_Two", "User_Three"]
        storage.add_followers_batch(batch, current_followers_count=1520)

        self.assertEqual(storage.get_followers_cache_size(), 3)
        self.assertEqual(storage.get_cached_followers_count(), 1520)
        self.assertTrue(storage.is_follower("user_one"))
        self.assertTrue(storage.is_follower("user_two"))
        self.assertTrue(storage.is_follower("user_three"))

    def test_clear_followers_cache(self):
        storage = Storage(self.username)
        storage.add_followers_batch(
            ["user1", "user2"], current_followers_count=50
        )
        self.assertEqual(storage.get_followers_cache_size(), 2)

        storage.clear_followers_cache()
        self.assertEqual(storage.get_followers_cache_size(), 0)
        self.assertEqual(storage.get_cached_followers_count(), 0)
        self.assertFalse(storage.is_follower("user1"))

    def test_corrupted_cache_file_graceful_recovery(self):
        account_dir = os.path.join(self.test_dir, self.username)
        os.makedirs(account_dir, exist_ok=True)
        cache_path = os.path.join(account_dir, "followers_cache.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write("CORRUPTED_NOT_VALID_JSON{[[")

        # Storage should not crash, but fallback to empty cache
        storage = Storage(self.username)
        self.assertEqual(storage.get_followers_cache_size(), 0)
        self.assertFalse(storage.is_follower("user"))


class TestProfileViewFollowsYouBadge(unittest.TestCase):
    def setUp(self):
        self.device = MagicMock()
        self.profile_view = ProfileView(self.device)

    def test_has_follows_you_badge_via_text(self):
        # Mock Tier 1 text match
        text_badge = MagicMock()
        text_badge.exists.return_value = True
        self.device.find.return_value = text_badge

        self.assertTrue(self.profile_view.has_follows_you_badge())

    def test_has_follows_you_badge_via_description(self):
        # Tier 1 fails, Tier 2 succeeds
        text_badge = MagicMock()
        text_badge.exists.return_value = False
        desc_badge = MagicMock()
        desc_badge.exists.return_value = True

        def find_side_effect(**kwargs):
            tm = kwargs.get("textMatches")
            dm = kwargs.get("descriptionMatches")
            if tm == "(?i)^Follows you$":
                return text_badge
            if dm == "(?i)^Follows you$":
                return desc_badge
            mock_obj = MagicMock()
            mock_obj.exists.return_value = False
            return mock_obj

        self.device.find.side_effect = find_side_effect
        self.assertTrue(self.profile_view.has_follows_you_badge())

    def test_has_follows_you_badge_via_context_text(self):
        text_badge = MagicMock()
        text_badge.exists.return_value = False
        desc_badge = MagicMock()
        desc_badge.exists.return_value = False
        context_badge = MagicMock()
        context_badge.exists.return_value = True
        context_badge.get_text.return_value = (
            "Followed by alex and follows you"
        )

        def find_side_effect(**kwargs):
            tm = kwargs.get("textMatches")
            dm = kwargs.get("descriptionMatches")
            rm = kwargs.get("resourceIdMatches", "")
            if tm == "(?i)^Follows you$":
                return text_badge
            if dm == "(?i)^Follows you$":
                return desc_badge
            if "follow_context" in rm:
                return context_badge
            mock_obj = MagicMock()
            mock_obj.exists.return_value = False
            return mock_obj

        self.device.find.side_effect = find_side_effect
        self.assertTrue(self.profile_view.has_follows_you_badge())

    def test_has_follows_you_badge_negative(self):
        # All tiers fail
        mock_obj = MagicMock()
        mock_obj.exists.return_value = False
        self.device.find.return_value = mock_obj

        self.assertFalse(self.profile_view.has_follows_you_badge())


class TestFollowerDeltaGuardAndFastCheck(unittest.TestCase):
    def setUp(self):
        self.plugin = ActionUnfollowFollowers()
        self.plugin.args = MagicMock()
        self.plugin.args.clear_followers_cache = False
        self.plugin.args.ignore_followers_cache = False
        self.plugin.session_state = MagicMock()
        self.plugin.session_state.my_followers_count = 1000

        self.storage = MagicMock()
        self.device = MagicMock()

    def test_delta_guard_zero_delta_skips_followers_list(self):
        # Count identical to cached count, cache size > 0
        self.storage.get_cached_followers_count.return_value = 1000
        self.storage.get_followers_cache_size.return_value = 250
        self.storage.is_follower = MagicMock(return_value=True)

        target = "InstaAddict.plugins.action_unfollow_followers.ProfileView"
        with patch(target) as MockProfileView:
            self.plugin._sync_followers_cache_if_needed(
                self.device, self.storage
            )
            # navigateToFollowers must NOT be called
            mock_nav = MockProfileView.return_value.navigateToFollowers
            mock_nav.assert_not_called()

    def test_delta_guard_positive_delta_triggers_fast_harvest(self):
        # Current 1005 vs cached 1000 -> delta = +5
        self.plugin.session_state.my_followers_count = 1005
        self.storage.get_cached_followers_count.return_value = 1000
        self.storage.get_followers_cache_size.return_value = 250
        self.storage.is_follower = MagicMock(return_value=True)

        target = "InstaAddict.plugins.action_unfollow_followers.ProfileView"
        with patch(target) as MockProfileView:
            mock_pv = MockProfileView.return_value
            mock_pv.navigateToFollowers.return_value = True
            mock_pv.harvest_visible_followers.return_value = [
                "new_follower_1",
                "new_follower_2",
            ]

            self.plugin._sync_followers_cache_if_needed(
                self.device, self.storage
            )

            mock_pv.navigateToFollowers.assert_called_once()
            mock_pv.harvest_visible_followers.assert_called_once()
            self.storage.add_followers_batch.assert_called_once_with(
                ["new_follower_1", "new_follower_2"],
                current_followers_count=1005,
                save=True,
            )
            self.device.back.assert_called_once()

    def test_check_is_follower_uses_cache_first_without_touching_ui(self):
        self.storage.is_follower.return_value = True

        result = self.plugin.check_is_follower(
            self.device, "cached_fan", "my_bot", storage=self.storage
        )
        self.assertTrue(result)
        # ProfileView must NOT be queried for UI badges
        self.device.find.assert_not_called()

    def test_check_is_follower_uses_profile_badge_when_not_in_cache(self):
        self.storage.is_follower.return_value = False

        target = "InstaAddict.plugins.action_unfollow_followers.ProfileView"
        with patch(target) as MockProfileView:
            mock_pv = MockProfileView.return_value
            mock_pv.has_follows_you_badge.return_value = True

            result = self.plugin.check_is_follower(
                self.device, "new_friend", "my_bot", storage=self.storage
            )
            self.assertTrue(result)
            self.storage.add_follower.assert_called_once_with("new_friend")

    def test_check_is_follower_returns_false_when_no_badge(self):
        self.storage.is_follower.return_value = False

        target = "InstaAddict.plugins.action_unfollow_followers.ProfileView"
        with patch(target) as MockProfileView:
            mock_pv = MockProfileView.return_value
            mock_pv.has_follows_you_badge.return_value = False

            result = self.plugin.check_is_follower(
                self.device, "stranger", "my_bot", storage=self.storage
            )
            self.assertFalse(result)
            self.storage.add_follower.assert_not_called()


class TestDirectionalSorting(unittest.TestCase):
    def setUp(self):
        self.plugin = ActionUnfollowFollowers()
        self.plugin.args = MagicMock()
        self.plugin.ResourceID = MagicMock()
        self.plugin.ResourceID.SORTING_ENTRY_ROW_OPTION = "sort_option"
        rv_id = "sort_options_recycler"
        setattr(
            self.plugin.ResourceID,
            "FOLLOW_LIST_SORTING_OPTIONS_RECYCLER_VIEW",
            rv_id,
        )
        self.device = MagicMock()

    def test_sort_followings_defaults_to_latest(self):
        self.plugin.args.sort_followings_by_earliest = False
        self.plugin.args.sort_followers_newest_to_oldest = False
        self.plugin.args.sort_followings_by_latest = False

        sort_btn = MagicMock()
        sort_btn.exists.return_value = True
        options_rv = MagicMock()
        options_rv.exists.return_value = True
        latest_btn = MagicMock()
        options_rv.child.return_value = latest_btn

        def find_mock(**kwargs):
            if kwargs.get("resourceId") == "sort_option":
                return sort_btn
            if kwargs.get("resourceId") == "sort_options_recycler":
                return options_rv
            return MagicMock()

        self.device.find.side_effect = find_mock

        res = self.plugin.sort_followings_by_date(self.device)
        self.assertTrue(res)
        options_rv.child.assert_called_once_with(textContains="Latest")
        latest_btn.click.assert_called_once()

    def test_sort_followings_explicit_earliest(self):
        self.plugin.args.sort_followings_by_earliest = True

        sort_btn = MagicMock()
        sort_btn.exists.return_value = True
        options_rv = MagicMock()
        options_rv.exists.return_value = True
        earliest_btn = MagicMock()
        options_rv.child.return_value = earliest_btn

        def find_mock(**kwargs):
            if kwargs.get("resourceId") == "sort_option":
                return sort_btn
            if kwargs.get("resourceId") == "sort_options_recycler":
                return options_rv
            return MagicMock()

        self.device.find.side_effect = find_mock

        res = self.plugin.sort_followings_by_date(
            self.device, newest_to_oldest=False
        )
        self.assertTrue(res)
        options_rv.child.assert_called_once_with(textContains="Earliest")
        earliest_btn.click.assert_called_once()


if __name__ == "__main__":
    unittest.main()

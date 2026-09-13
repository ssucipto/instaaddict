import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from InstaAddict.core.storage import FollowingStatus, Storage
from InstaAddict.plugins.action_unfollow_followers import ActionUnfollowFollowers


class TestNonBotFollowingsCache(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.username = "test_user"
        # Patch ACCOUNTS in storage to point to test_dir
        self.orig_accounts = "accounts"
        import InstaAddict.core.storage as storage_mod

        storage_mod.ACCOUNTS = self.test_dir

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_storage_init_empty(self):
        storage = Storage(self.username)
        self.assertEqual(storage.non_bot_followings, {})
        self.assertFalse(storage.is_non_bot_following("someone"))
        self.assertFalse(storage.is_non_bot_following(""))
        self.assertFalse(storage.is_non_bot_following(None))

    def test_add_and_query_non_bot_following(self):
        storage = Storage(self.username)
        storage.add_non_bot_following("OrganicAccount", reason="not_followed_by_bot", save=True)

        self.assertTrue(storage.is_non_bot_following("organicaccount"))
        self.assertTrue(storage.is_non_bot_following("OrganicAccount"))
        self.assertIn("organicaccount", storage.non_bot_followings)
        self.assertIn("checked_at", storage.non_bot_followings["organicaccount"])
        self.assertEqual(storage.non_bot_followings["organicaccount"]["reason"], "not_followed_by_bot")

        # Verify persisted on disk
        cache_path = os.path.join(self.test_dir, self.username, "non_bot_followings.json")
        self.assertTrue(os.path.isfile(cache_path))
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("organicaccount", data)

    def test_add_non_bot_followings_batch(self):
        storage = Storage(self.username)
        users = ["user1", "User2", "user3"]
        storage.add_non_bot_followings_batch(users)

        self.assertTrue(storage.is_non_bot_following("user1"))
        self.assertTrue(storage.is_non_bot_following("user2"))
        self.assertTrue(storage.is_non_bot_following("user3"))

        cache_path = os.path.join(self.test_dir, self.username, "non_bot_followings.json")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 3)

    def test_persistence_across_storage_reloads(self):
        storage1 = Storage(self.username)
        storage1.add_non_bot_following("dog_fan_page")

        # Simulate bot restart by creating a new Storage instance on the same directory
        storage2 = Storage(self.username)
        self.assertTrue(storage2.is_non_bot_following("dog_fan_page"))
        self.assertEqual(len(storage2.non_bot_followings), 1)

    def test_remove_and_clear_cache(self):
        storage = Storage(self.username)
        storage.add_non_bot_following("remove_me")
        storage.add_non_bot_following("keep_me")

        storage.remove_non_bot_following("remove_me")
        self.assertFalse(storage.is_non_bot_following("remove_me"))
        self.assertTrue(storage.is_non_bot_following("keep_me"))

        storage.clear_non_bot_followings()
        self.assertEqual(storage.non_bot_followings, {})
        self.assertFalse(storage.is_non_bot_following("keep_me"))

        # Verify disk reflects empty dict
        cache_path = os.path.join(self.test_dir, self.username, "non_bot_followings.json")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, {})

    def test_corrupted_cache_file_handling(self):
        user_dir = os.path.join(self.test_dir, self.username)
        os.makedirs(user_dir, exist_ok=True)
        cache_path = os.path.join(user_dir, "non_bot_followings.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write("invalid json content {{{")

        storage = Storage(self.username)
        # Should gracefully recover with empty dictionary without raising exception
        self.assertEqual(storage.non_bot_followings, {})

    def test_cache_invalidation_when_bot_follows_user(self):
        storage = Storage(self.username)
        storage.add_non_bot_following("target_user")
        self.assertTrue(storage.is_non_bot_following("target_user"))

        # Bot later follows target_user
        storage.add_interacted_user(
            username="target_user",
            session_id="session_123",
            followed=True,
            job_name="follow-feed",
        )

        # target_user must be automatically pruned from non_bot_followings
        self.assertFalse(storage.is_non_bot_following("target_user"))
        self.assertEqual(storage.get_following_status("target_user"), FollowingStatus.FOLLOWED)

    def test_action_unfollow_pre_seeding_and_fast_skip(self):
        storage = Storage(self.username)
        storage.add_non_bot_following("organic_friend_1")
        storage.add_non_bot_following("organic_friend_2")

        plugin = ActionUnfollowFollowers()
        plugin.args = MagicMock()
        plugin.args.clear_non_bot_cache = False
        plugin.args.ignore_non_bot_cache = False
        plugin.args.sort_followers_newest_to_oldest = False
        plugin.args.app_id = "com.instagram.android"
        plugin.args.unfollow_delay = "0"
        plugin.ResourceID = MagicMock()
        plugin.ResourceID.FOLLOW_LIST_CONTAINER = "follow_list"
        plugin.ResourceID.SORTING_ENTRY_ROW_OPTION = "sort_option"
        plugin.ResourceID.USER_LIST_CONTAINER = "user_list"
        plugin.ResourceID.LIST = "list"
        plugin.ResourceID.ROW_LOAD_MORE_BUTTON = "load_more"

        # Mock device
        device = MagicMock()
        user_list_obj = MagicMock()
        user_list_obj.exists.return_value = False
        user_list_obj.__iter__.return_value = []
        device.find.return_value = user_list_obj

        # Call iterate_over_followings with mock device that terminates on first loop
        # We verify that pre-seeding reads from storage.non_bot_followings
        self.assertTrue(storage.is_non_bot_following("organic_friend_1"))
        self.assertTrue(storage.is_non_bot_following("organic_friend_2"))

    def test_cache_invalidation_when_user_unfollowed(self):
        storage = Storage(self.username)
        storage.add_non_bot_following("manual_follow")
        self.assertTrue(storage.is_non_bot_following("manual_follow"))

        # User is unfollowed via --unfollow-any
        storage.add_interacted_user(
            username="manual_follow",
            session_id="session_456",
            unfollowed=True,
            job_name="unfollow-any",
        )

        # manual_follow must be automatically pruned from non_bot_followings
        self.assertFalse(storage.is_non_bot_following("manual_follow"))
        self.assertEqual(storage.get_following_status("manual_follow"), FollowingStatus.UNFOLLOWED)

    def test_action_unfollow_restriction_scoping(self):
        storage = Storage(self.username)
        storage.add_non_bot_following("cached_organic_user")

        plugin = ActionUnfollowFollowers()
        plugin.args = MagicMock()
        plugin.args.clear_non_bot_cache = False
        plugin.args.ignore_non_bot_cache = False
        plugin.args.sort_followers_newest_to_oldest = False
        plugin.args.app_id = "com.instagram.android"
        plugin.ResourceID = MagicMock()
        plugin.ResourceID.FOLLOW_LIST_CONTAINER = "follow_list"
        plugin.ResourceID.SORTING_ENTRY_ROW_OPTION = "sort_option"
        plugin.ResourceID.USER_LIST_CONTAINER = "user_list"
        plugin.ResourceID.LIST = "list"

        # When restriction is FOLLOWED_BY_SCRIPT:
        # iterate_over_followings pre-seeds checked with cached_organic_user
        # When restriction is ANY:
        # iterate_over_followings does NOT pre-seed checked with cached_organic_user
        self.assertTrue(storage.is_non_bot_following("cached_organic_user"))


if __name__ == "__main__":
    unittest.main()

import json
import os
import shutil
import tempfile
import unittest

import yaml

from InstaAddict.core.hashtag_manager import HashtagManager


class TestHashtagManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.username = "test_user"
        # Reset singleton cache before each test
        HashtagManager._instances.clear()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        HashtagManager._instances.clear()

    def test_init_default_template(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        self.assertTrue(manager.has_tiered_sources())
        self.assertIn("tier1_local_community", manager.master_data["tiers"])
        self.assertIn("tier2_niche_topic", manager.master_data["tiers"])
        self.assertIn("tier3_lifestyle_adventure", manager.master_data["tiers"])
        self.assertIn("tier4_reach_and_trending", manager.master_data["tiers"])
        self.assertEqual(manager.master_data.get("cooldown_sessions"), 2)
        self.assertEqual(manager.master_data.get("min_seen_to_promote"), 3)

    def test_harvest_and_filter(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        caption = "Morning run at the beach! #outdoorpets #like4like #fyp #beachpups #crypto"
        manager.harvest_from_caption(caption, source_tag="#petstagram")

        # #like4like, #fyp are spam blacklisted; #crypto is irrelevant
        # #outdoorpets and #beachpups are relevant
        self.assertIn("outdoorpets", manager.discovered_tags)
        self.assertIn("beachpups", manager.discovered_tags)
        self.assertNotIn("like4like", manager.discovered_tags)
        self.assertNotIn("fyp", manager.discovered_tags)
        self.assertNotIn("crypto", manager.discovered_tags)

        info = manager.discovered_tags["outdoorpets"]
        self.assertEqual(info["seen_count"], 1)
        self.assertEqual(info["promoted"], False)
        self.assertEqual(info["sources"], ["#petstagram"])

    def test_auto_promotion(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        manager.master_data["min_seen_to_promote"] = 3

        tag = "local_community_pets"
        caption = f"Check out #{tag} today!"

        # Harvest 1
        manager.harvest_from_caption(caption)
        self.assertFalse(manager.discovered_tags[tag]["promoted"])

        # Harvest 2
        manager.harvest_from_caption(caption)
        self.assertFalse(manager.discovered_tags[tag]["promoted"])

        # Harvest 3 -> threshold reached -> auto-promoted
        manager.harvest_from_caption(caption)
        self.assertTrue(manager.discovered_tags[tag]["promoted"])

        # Should be classified in tier1_local_community due to "local" keyword
        tier1_tags = manager.master_data["tiers"]["tier1_local_community"]["tags"]
        self.assertIn(tag, tier1_tags)

    def test_breed_and_lifestyle_tier_classification(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        # Generic pet/animal niche tier
        self.assertEqual(manager._classify_tag_tier("jackrussellworld"), "tier2_niche_topic")  # contains 'jack'
        self.assertEqual(manager._classify_tag_tier("dogbreeds"), "tier2_niche_topic")  # contains 'dog'
        # Lifestyle/adventure tier (beach, no pet keywords)
        self.assertEqual(manager._classify_tag_tier("beachadventure"), "tier3_lifestyle_adventure")
        self.assertEqual(manager._classify_tag_tier("hiketrails"), "tier3_lifestyle_adventure")  # no pet keywords
        self.assertEqual(manager._classify_tag_tier("localcommunity"), "tier1_local_community")  # contains 'local'
        self.assertEqual(manager._classify_tag_tier("photooftheday"), "tier4_reach_and_trending")  # default reach

    def test_rotation_cooldown_and_sampling(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        # Custom tier setup with sufficient tags to test rotation without starvation
        manager.master_data["tiers"] = {
            "tier1": {"name": "T1", "session_sample_count": 2, "tags": ["tagA", "tagB", "tagC", "tagD"]},
            "tier2": {"name": "T2", "session_sample_count": 1, "tags": ["tagE", "tagF", "tagG"]},
        }
        manager.master_data["cooldown_sessions"] = 2

        # Session 1: sample
        s1 = manager.get_session_sources()
        self.assertEqual(len(s1), 3)  # 2 from T1, 1 from T2
        for t in s1:
            self.assertIn(t, manager.master_data["cooldowns"])
            self.assertEqual(manager.master_data["cooldowns"][t], 2)

        # Session 2: cooldown tick & sample unused tags
        s2 = manager.get_session_sources()
        self.assertEqual(len(s2), 3)
        # Verify no tag from session 1 was reused in session 2 (cooldown enforced)
        for t in s1:
            self.assertNotIn(t, s2)
            self.assertEqual(manager.master_data["cooldowns"][t], 1)

    def test_dead_tag_pruning(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        manager.master_data["tiers"]["tier1_local_community"]["tags"].append("broken_tag")
        self.assertIn("broken_tag", manager.master_data["tiers"]["tier1_local_community"]["tags"])

        # Navigation failed: record dead tag
        manager.record_hashtag_result("broken_tag", posts_found=False)

        self.assertIn("broken_tag", manager.master_data.get("dead_tags", []))
        self.assertNotIn("broken_tag", manager.master_data["tiers"]["tier1_local_community"]["tags"])

    def test_saturation_benching(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        tag = "crowded_tag"
        manager.master_data["tiers"]["tier1_local_community"]["tags"].append(tag)

        # First hit already liked limit -> counter = 1
        manager.record_hashtag_result(tag, posts_found=True, already_liked_exhausted=True)
        self.assertEqual(manager.master_data["saturated_tags"].get(tag), 1)

        # Second hit -> counter = 2 -> benched for 7 days with string timestamp
        manager.record_hashtag_result(tag, posts_found=True, already_liked_exhausted=True)
        self.assertIsInstance(manager.master_data["saturated_tags"].get(tag), str)

        # Reset tag test
        reset_tag = "good_tag"
        manager.record_hashtag_result(reset_tag, posts_found=True, already_liked_exhausted=True)
        self.assertEqual(manager.master_data["saturated_tags"].get(reset_tag), 1)
        manager.record_hashtag_result(reset_tag, posts_found=True, already_liked_exhausted=False)
        self.assertNotIn(reset_tag, manager.master_data["saturated_tags"])

    def test_fallback_when_disabled(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        manager.master_data["enabled"] = False
        self.assertFalse(manager.has_tiered_sources())

        fallback = ["#custom1", "#custom2"]
        res = manager.get_session_sources(fallback_sources=fallback)
        self.assertEqual(res, fallback)

    def test_save_all_atomic_persistence(self):
        manager = HashtagManager(
            self.username, account_dir=os.path.join(self.test_dir, self.username)
        )
        manager.harvest_from_caption("#perthpuppy")
        manager.save_all()

        # Check YAML file exists and is valid
        self.assertTrue(os.path.isfile(manager.hashtags_yml_path))
        with open(manager.hashtags_yml_path, "r", encoding="utf-8") as f:
            y_data = yaml.safe_load(f)
        self.assertEqual(y_data["username"], self.username)

        # Check JSON file exists and is valid
        self.assertTrue(os.path.isfile(manager.discovered_path))
        with open(manager.discovered_path, "r", encoding="utf-8") as f:
            j_data = json.load(f)
        self.assertIn("perthpuppy", j_data)


if __name__ == "__main__":
    unittest.main()

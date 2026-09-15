import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import yaml

from InstaAddict.plugins.upload_posts import (
    ALLOWED_EXTENSIONS,
    DEFAULT_RATE_LIMIT_HOURS,
    UploadPostsPlugin,
)


class TestUploadPostsPlugin(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        self.plugin = UploadPostsPlugin()

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_plugin_arguments(self):
        """Test argument definitions and presence of required metadata."""
        args_by_name = {arg["arg"]: arg for arg in self.plugin.arguments}
        self.assertIn("--upload-posts", args_by_name)
        self.assertTrue(args_by_name["--upload-posts"].get("operation"))

        self.assertIn("--upload-rate-limit-hours", args_by_name)
        rate_arg = args_by_name["--upload-rate-limit-hours"]
        self.assertIn("metavar", rate_arg)
        self.assertEqual(rate_arg["metavar"], "12.0")
        self.assertEqual(rate_arg["type"], float)

        self.assertIn("--upload-queue-dir", args_by_name)
        queue_arg = args_by_name["--upload-queue-dir"]
        self.assertIn("metavar", queue_arg)
        self.assertEqual(queue_arg["metavar"], "path/to/queue")

    def test_resolve_username_from_cli(self):
        """CLI argument takes highest priority for username resolution."""
        configs = MagicMock()
        configs.args.username = "cli_user"
        configs.args.config = "accounts/other_user/config.yml"
        sessions = [MagicMock(my_username="session_user")]

        user = self.plugin._resolve_username(configs, sessions)
        self.assertEqual(user, "cli_user")

    def test_resolve_username_from_session(self):
        """Session my_username is used if CLI argument is not specified."""
        configs = MagicMock()
        configs.args.username = None
        configs.args.config = "accounts/config_user/config.yml"
        sessions = [MagicMock(my_username="session_user")]

        user = self.plugin._resolve_username(configs, sessions)
        self.assertEqual(user, "session_user")

    def test_resolve_username_from_config_path(self):
        """Parses username from config path when CLI and session username are absent."""
        configs = MagicMock()
        configs.args.username = None
        sessions = []

        # Posix path
        configs.args.config = "accounts/dog_account/config.yml"
        self.assertEqual(self.plugin._resolve_username(configs, sessions), "dog_account")

        # Windows path
        configs.args.config = r"accounts\cat_account\config.yml"
        self.assertEqual(self.plugin._resolve_username(configs, sessions), "cat_account")

    def test_get_rate_limit_hours_cli_override(self):
        """CLI flag overrides config file and default."""
        configs = MagicMock()
        configs.args.upload_rate_limit_hours = 4.5
        config_path = os.path.join(self.test_dir, "config.yml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump({"upload-rate-limit-hours": 8.0}, f)

        rate = self.plugin._get_rate_limit_hours(configs, config_path)
        self.assertEqual(rate, 4.5)

    def test_get_rate_limit_hours_yaml_config(self):
        """YAML config setting is used when CLI flag is None."""
        configs = MagicMock()
        configs.args.upload_rate_limit_hours = None
        config_path = os.path.join(self.test_dir, "config.yml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump({"upload-rate-limit-hours": 6.0}, f)

        rate = self.plugin._get_rate_limit_hours(configs, config_path)
        self.assertEqual(rate, 6.0)

    def test_get_rate_limit_hours_default(self):
        """Falls back to DEFAULT_RATE_LIMIT_HOURS (12.0) when nothing is specified."""
        configs = MagicMock()
        configs.args.upload_rate_limit_hours = None
        rate = self.plugin._get_rate_limit_hours(configs, "")
        self.assertEqual(rate, DEFAULT_RATE_LIMIT_HOURS)

    def test_is_rate_limited_disabled_with_zero(self):
        """Rate limiting is disabled if hours <= 0."""
        published_dir = os.path.join(self.test_dir, "published")
        os.makedirs(published_dir, exist_ok=True)
        # Create recent file
        test_file = os.path.join(published_dir, "recent.jpg")
        with open(test_file, "w") as f:
            f.write("test")

        self.assertFalse(self.plugin._is_rate_limited(published_dir, rate_limit_hours=0.0))
        self.assertFalse(self.plugin._is_rate_limited(published_dir, rate_limit_hours=-1.0))

    def test_is_rate_limited_active(self):
        """Returns True if a media file was published within the rate limit window."""
        published_dir = os.path.join(self.test_dir, "published")
        os.makedirs(published_dir, exist_ok=True)
        media_file = os.path.join(published_dir, "photo.JPG")
        with open(media_file, "w") as f:
            f.write("test")

        # Set mtime to 2 hours ago
        two_hours_ago = (datetime.now() - timedelta(hours=2)).timestamp()
        os.utime(media_file, (two_hours_ago, two_hours_ago))

        # With a 12-hour limit, it should be rate limited
        self.assertTrue(self.plugin._is_rate_limited(published_dir, rate_limit_hours=12.0))
        # With a 1-hour limit, it should NOT be rate limited
        self.assertFalse(self.plugin._is_rate_limited(published_dir, rate_limit_hours=1.0))

    @patch("InstaAddict.plugins.upload_posts.get_vision_caption")
    def test_extract_caption_txt_feeds_vision_ai_guidance(self, mock_vision):
        """Verifies that .txt sidecar is passed into Gemini Vision AI as contextual guidance and extended."""
        mock_vision.return_value = "Extended: Lola enjoying the sunny beach #jackrussell #perth"
        pending_dir = os.path.join(self.test_dir, "pending")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "photo.JPG"
        media_path = os.path.join(pending_dir, media_file)
        with open(os.path.join(pending_dir, "photo.txt"), "w", encoding="utf-8") as f:
            f.write("Caption from TXT sidecar #dogs")

        with open(os.path.join(pending_dir, "photo.json"), "w", encoding="utf-8") as f:
            json.dump({"caption": "Caption from JSON sidecar"}, f)

        caption = self.plugin._extract_caption(pending_dir, media_file, "")
        mock_vision.assert_called_once_with(
            media_path, "casual Instagram user", user_context="Caption from TXT sidecar #dogs"
        )
        self.assertEqual(caption, "Extended: Lola enjoying the sunny beach #jackrussell #perth")

    @patch("InstaAddict.plugins.upload_posts.get_vision_caption")
    def test_extract_caption_txt_fallback_on_ai_failure(self, mock_vision):
        """Verifies that if Vision AI is unavailable or fails, it falls back to raw .txt content."""
        mock_vision.return_value = ""
        pending_dir = os.path.join(self.test_dir, "pending")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "photo.JPG"
        with open(os.path.join(pending_dir, "photo.txt"), "w", encoding="utf-8") as f:
            f.write("Caption from TXT sidecar #dogs")

        caption = self.plugin._extract_caption(pending_dir, media_file, "")
        self.assertEqual(caption, "Caption from TXT sidecar #dogs")

    def test_extract_caption_json_fallback(self):
        """Verifies that .json sidecar is used when .txt sidecar is absent."""
        pending_dir = os.path.join(self.test_dir, "pending")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "photo.JPG"
        with open(os.path.join(pending_dir, "photo.json"), "w", encoding="utf-8") as f:
            json.dump({"caption": "Caption from JSON sidecar #puppy"}, f)

        caption = self.plugin._extract_caption(pending_dir, media_file, "")
        self.assertEqual(caption, "Caption from JSON sidecar #puppy")

    @patch("InstaAddict.plugins.upload_posts.get_vision_caption")
    def test_extract_caption_vision_ai_fallback(self, mock_vision):
        """Falls back to Gemini Vision AI when no sidecar file is present."""
        mock_vision.return_value = "AI Generated Caption #adventure"
        pending_dir = os.path.join(self.test_dir, "pending")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "photo.png"
        caption = self.plugin._extract_caption(pending_dir, media_file, "")
        self.assertEqual(caption, "AI Generated Caption #adventure")
        mock_vision.assert_called_once_with(
            os.path.join(pending_dir, media_file), "casual Instagram user", user_context=""
        )

    def test_case_insensitive_media_extensions(self):
        """Verifies uppercase extensions (.JPG, .PNG, .MP4) are discovered."""
        pending_dir = os.path.join(self.test_dir, "pending")
        os.makedirs(pending_dir, exist_ok=True)

        valid_files = [
            "DSCF2934.JPG",
            "photo.jpeg",
            "BANNER.PNG",
            "clip.MP4",
            "lower.jpg",
        ]
        ignored_files = [
            "notes.txt",
            "caption.json",
            "config.yml",
            "script.py",
        ]

        for fname in valid_files + ignored_files:
            with open(os.path.join(pending_dir, fname), "w") as f:
                f.write("test")

        all_files = sorted(os.listdir(pending_dir))
        matched = [f for f in all_files if f.lower().endswith(ALLOWED_EXTENSIONS)]

        self.assertEqual(sorted(matched), sorted(valid_files))

    @patch.object(UploadPostsPlugin, "_upload_to_ig")
    def test_run_success_lifecycle(self, mock_upload):
        """Verifies successful upload archives media and sidecars and records metrics."""
        mock_upload.return_value = True

        os.chdir(self.test_dir)
        account_dir = os.path.join("accounts", "test_user")
        pending_dir = os.path.join(account_dir, "content_queue", "pending")
        published_dir = os.path.join(account_dir, "content_queue", "published")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "DSCF2934.JPG"
        with open(os.path.join(pending_dir, media_file), "w") as f:
            f.write("fake image data")
        with open(os.path.join(pending_dir, "DSCF2934.txt"), "w", encoding="utf-8") as f:
            f.write("Lola enjoying the sun! #jackrussell")
        with open(os.path.join(pending_dir, "DSCF2934.json"), "w", encoding="utf-8") as f:
            json.dump({"caption": "fallback json"}, f)

        configs = MagicMock()
        configs.args.username = "test_user"
        configs.args.config = os.path.join(account_dir, "config.yml")
        configs.args.upload_rate_limit_hours = 0.0

        session = MagicMock()
        session.totalUploadsSuccess = 0
        session.uploadHistory = []
        sessions = [session]

        device = MagicMock()
        self.plugin.run(device, configs, None, sessions, None, "upload-posts")

        self.assertTrue(mock_upload.called)
        self.assertEqual(session.totalUploadsSuccess, 1)
        self.assertEqual(len(session.uploadHistory), 1)
        self.assertEqual(session.uploadHistory[0]["status"], "success")

        # Verify media and sidecars are moved to published/
        self.assertTrue(os.path.exists(os.path.join(published_dir, media_file)))
        self.assertTrue(os.path.exists(os.path.join(published_dir, "DSCF2934.txt")))
        self.assertTrue(os.path.exists(os.path.join(published_dir, "DSCF2934.json")))
        self.assertFalse(os.path.exists(os.path.join(pending_dir, media_file)))

    @patch.object(UploadPostsPlugin, "_upload_to_ig")
    def test_run_failure_lifecycle(self, mock_upload):
        """Verifies failed upload leaves media in pending and records failure metrics."""
        mock_upload.return_value = False

        os.chdir(self.test_dir)
        account_dir = os.path.join("accounts", "test_user")
        pending_dir = os.path.join(account_dir, "content_queue", "pending")
        published_dir = os.path.join(account_dir, "content_queue", "published")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "DSCF2934.JPG"
        with open(os.path.join(pending_dir, media_file), "w") as f:
            f.write("fake image data")

        configs = MagicMock()
        configs.args.username = "test_user"
        configs.args.config = os.path.join(account_dir, "config.yml")
        configs.args.upload_rate_limit_hours = 0.0

        session = MagicMock()
        session.totalUploadsFailed = 0
        session.uploadHistory = []
        sessions = [session]

        device = MagicMock()
        self.plugin.run(device, configs, None, sessions, None, "upload-posts")

        self.assertTrue(mock_upload.called)
        self.assertEqual(session.totalUploadsFailed, 1)
        self.assertEqual(len(session.uploadHistory), 1)
        self.assertEqual(session.uploadHistory[0]["status"], "failed")

        # Verify media remains in pending/
        self.assertTrue(os.path.exists(os.path.join(pending_dir, media_file)))
        self.assertFalse(os.path.exists(os.path.join(published_dir, media_file)))

    @patch.object(UploadPostsPlugin, "_upload_to_ig", return_value=True)
    def test_custom_upload_queue_dir(self, mock_upload):
        """Verifies that --upload-queue-dir correctly routes to custom directory."""
        custom_dir = os.path.join(self.test_dir, "my_custom_queue", "pending")
        published_dir = os.path.join(self.test_dir, "my_custom_queue", "published")
        os.makedirs(custom_dir, exist_ok=True)

        media_file = "custom_dog.png"
        with open(os.path.join(custom_dir, media_file), "w") as f:
            f.write("custom img")

        configs = MagicMock()
        configs.args.username = "custom_user"
        configs.args.upload_queue_dir = custom_dir
        configs.args.upload_rate_limit_hours = 0.0

        session = MagicMock()
        session.totalUploadsSuccess = 0
        session.uploadHistory = []
        sessions = [session]

        device = MagicMock()
        self.plugin.run(device, configs, None, sessions, None, "upload-posts")

        self.assertTrue(mock_upload.called)
        self.assertEqual(session.totalUploadsSuccess, 1)
        self.assertTrue(os.path.exists(os.path.join(published_dir, media_file)))

    def test_mediastore_id_parsing(self):
        """Verifies regex extraction of _id from content query output."""
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(
                stdout=(
                    "Row: 0 _id=35, _data=/storage/emulated/0/screen1.png\n"
                    "Row: 1 _id=52, _data=/storage/emulated/0/Pictures/DSCF2934.JPG\n"
                    "Row: 2 _id=53, _data=/storage/emulated/0/Pictures/other.png\n"
                )
            )
            media_id = self.plugin._get_mediastore_id("emulator-5554", "DSCF2934.JPG")
            self.assertEqual(media_id, "52")

    def test_mediastore_id_parsing_picks_highest_id(self):
        """Verifies that the newest/highest ID is selected when multiple entries match."""
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(
                stdout=(
                    "Row: 0 _id=12, _data=/storage/emulated/0/Pictures/photo.jpg\n"
                    "Row: 1 _id=99, _data=/storage/emulated/0/Pictures/photo.jpg\n"
                    "Row: 2 _id=45, _data=/storage/emulated/0/Pictures/other.png\n"
                )
            )
            media_id = self.plugin._get_mediastore_id("emulator-5554", "photo.jpg")
            self.assertEqual(media_id, "99")

    def test_execute_adb_timeout_handling(self):
        """Verifies that ADB timeout returns False safely without crashing."""
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="adb", timeout=5)):
            result = self.plugin._execute_adb("emulator-5554", ["push", "a", "b"], timeout=5)
            self.assertFalse(result)

    @patch.object(UploadPostsPlugin, "_upload_to_ig", side_effect=RuntimeError("Device detached"))
    def test_run_upload_unexpected_exception_recorded_as_failed(self, mock_upload):
        """Verifies that unexpected exceptions during upload do not crash run() and record failure metrics."""
        os.chdir(self.test_dir)
        account_dir = os.path.join("accounts", "test_user")
        pending_dir = os.path.join(account_dir, "content_queue", "pending")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "test_img.JPG"
        with open(os.path.join(pending_dir, media_file), "w") as f:
            f.write("data")

        configs = MagicMock()
        configs.args.username = "test_user"
        configs.args.config = os.path.join(account_dir, "config.yml")
        configs.args.upload_rate_limit_hours = 0.0

        session = MagicMock()
        session.totalUploadsFailed = 0
        session.uploadHistory = []
        sessions = [session]

        device = MagicMock()
        # Should not raise exception
        self.plugin.run(device, configs, None, sessions, None, "upload-posts")

        self.assertEqual(session.totalUploadsFailed, 1)
        self.assertEqual(len(session.uploadHistory), 1)
        self.assertEqual(session.uploadHistory[0]["status"], "failed")

    @patch.object(UploadPostsPlugin, "_upload_to_ig", return_value=True)
    def test_rate_limit_mtime_touched_on_publish(self, mock_upload):
        """Verifies that file mtime is updated to current time upon publishing."""
        import time
        os.chdir(self.test_dir)
        account_dir = os.path.join("accounts", "test_user")
        pending_dir = os.path.join(account_dir, "content_queue", "pending")
        published_dir = os.path.join(account_dir, "content_queue", "published")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "old_photo.jpg"
        media_path = os.path.join(pending_dir, media_file)
        with open(media_path, "w") as f:
            f.write("photo data")

        # Set old mtime from 48 hours ago
        old_time = time.time() - (48 * 3600)
        os.utime(media_path, (old_time, old_time))

        configs = MagicMock()
        configs.args.username = "test_user"
        configs.args.config = os.path.join(account_dir, "config.yml")
        configs.args.upload_rate_limit_hours = 0.0

        session = MagicMock()
        session.totalUploadsSuccess = 0
        session.uploadHistory = []
        sessions = [session]

        device = MagicMock()
        self.plugin.run(device, configs, None, sessions, None, "upload-posts")

        published_file = os.path.join(published_dir, media_file)
        self.assertTrue(os.path.exists(published_file))
        new_mtime = os.path.getmtime(published_file)
        # Should be updated to within last 5 seconds
        self.assertAlmostEqual(new_mtime, time.time(), delta=5)

    def test_sidecar_utf8_sig_bom_stripped(self):
        """Verifies that UTF-8 BOM (\ufeff) is cleanly stripped from sidecars."""
        pending_dir = os.path.join(self.test_dir, "pending")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "bom_photo.jpg"
        # Write file with explicit UTF-8 BOM
        with open(os.path.join(pending_dir, "bom_photo.txt"), "wb") as f:
            f.write("\ufeffCaption with Windows BOM #test".encode("utf-8"))

        with patch("InstaAddict.plugins.upload_posts.get_vision_caption") as mock_vision:
            mock_vision.return_value = ""  # Force fallback to raw txt
            caption = self.plugin._extract_caption(pending_dir, media_file, "")
            self.assertEqual(caption, "Caption with Windows BOM #test")
            self.assertFalse(caption.startswith("\ufeff"))

    def test_hashtag_enrichment_from_manager(self):
        """Verifies that captions with fewer than 3 hashtags are enriched from HashtagManager."""
        with patch("InstaAddict.core.hashtag_manager.HashtagManager.get_post_hashtags") as mock_tags:
            mock_tags.return_value = ["perthdogs", "jrt", "beachvibes"]
            raw_caption = "Sunny day out with the pup!"
            enriched = self.plugin._enrich_hashtags_if_needed(raw_caption, "test_user")
            self.assertIn("#perthdogs", enriched)
            self.assertIn("#jrt", enriched)
            self.assertIn("#beachvibes", enriched)
            self.assertTrue(enriched.startswith(raw_caption))

    def test_hashtag_enrichment_not_needed_if_already_tagged(self):
        """Verifies that captions with 3 or more hashtags are not bloated with duplicate tags."""
        with patch("InstaAddict.core.hashtag_manager.HashtagManager.get_post_hashtags") as mock_tags:
            mock_tags.return_value = ["perthdogs", "jrt"]
            tagged_caption = "Awesome sunset #sunset #beach #vibes #wa"
            result = self.plugin._enrich_hashtags_if_needed(tagged_caption, "test_user")
            self.assertEqual(result, tagged_caption)
            mock_tags.assert_not_called()


if __name__ == "__main__":
    unittest.main()



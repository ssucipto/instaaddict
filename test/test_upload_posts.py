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

    def test_extract_caption_txt_priority(self):
        """Verifies that .txt sidecar is read and preferred over .json sidecar."""
        pending_dir = os.path.join(self.test_dir, "pending")
        os.makedirs(pending_dir, exist_ok=True)

        media_file = "photo.JPG"
        with open(os.path.join(pending_dir, "photo.txt"), "w", encoding="utf-8") as f:
            f.write("Caption from TXT sidecar #dogs")

        with open(os.path.join(pending_dir, "photo.json"), "w", encoding="utf-8") as f:
            json.dump({"caption": "Caption from JSON sidecar"}, f)

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
        mock_vision.assert_called_once()

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


if __name__ == "__main__":
    unittest.main()

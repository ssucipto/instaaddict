import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from InstaAddict.plugins.telegram import (
    check_telegram_inbox,
    get_adb_device_status,
    get_upload_cooldown_status,
    trigger_on_demand_upload,
    _ACTIVE_UPLOADS,
    _UPLOAD_LOCK,
)


class TestTelegramCommands(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.username = "test_user"
        self.user_dir = os.path.join(self.test_dir, "accounts", self.username)
        self.pending_dir = os.path.join(self.user_dir, "content_queue", "pending")
        self.published_dir = os.path.join(self.user_dir, "content_queue", "published")
        os.makedirs(self.pending_dir, exist_ok=True)
        os.makedirs(self.published_dir, exist_ok=True)
        with _UPLOAD_LOCK:
            _ACTIVE_UPLOADS.clear()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        with _UPLOAD_LOCK:
            _ACTIVE_UPLOADS.clear()

    @patch("subprocess.run")
    def test_get_adb_device_status_online(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="List of devices attached\nemulator-5554\tdevice\n"
        )
        status = get_adb_device_status()
        self.assertIn("emulator-5554", status)
        self.assertIn("online", status)

    @patch("subprocess.run")
    def test_get_adb_device_status_offline(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="List of devices attached\nemulator-5554\toffline\n"
        )
        status = get_adb_device_status()
        self.assertIn("emulator-5554", status)
        self.assertIn("offline", status)

    @patch("subprocess.run")
    def test_get_adb_device_status_no_devices(self, mock_run):
        mock_run.return_value = MagicMock(stdout="List of devices attached\n\n")
        status = get_adb_device_status()
        self.assertIn("No ADB devices connected", status)

    def test_get_upload_cooldown_status_empty_published(self):
        with patch("os.path.exists", return_value=False):
            is_limited, elapsed, remaining = get_upload_cooldown_status(
                self.username, rate_limit_hours=12.0
            )
            self.assertFalse(is_limited)
            self.assertEqual(remaining, 0.0)

    def test_get_upload_cooldown_status_recent_file(self):
        # Create a file in published with current timestamp
        recent_file = os.path.join(self.published_dir, "recent_post.jpg")
        with open(recent_file, "w") as f:
            f.write("dummy")

        with patch(
            "InstaAddict.plugins.telegram.os.walk",
            return_value=[(self.published_dir, [], ["recent_post.jpg"])],
        ), patch(
            "InstaAddict.plugins.telegram.os.path.exists", return_value=True
        ):
            is_limited, elapsed, remaining = get_upload_cooldown_status(
                self.username, rate_limit_hours=12.0
            )
            self.assertTrue(is_limited)
            self.assertGreater(remaining, 0.0)

    @patch("subprocess.Popen")
    def test_trigger_on_demand_upload(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("ok", "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        started = trigger_on_demand_upload(self.username, force=True)
        self.assertTrue(started)

        # Check that calling it again while in active uploads is rejected
        with _UPLOAD_LOCK:
            _ACTIVE_UPLOADS.add(self.username)
        duplicate = trigger_on_demand_upload(self.username, force=True)
        self.assertFalse(duplicate)

    @patch("InstaAddict.plugins.telegram.telegram_bot_send_text")
    @patch("InstaAddict.plugins.telegram.telegram_bot_get_updates")
    def test_check_telegram_inbox_help(self, mock_updates, mock_send_text):
        mock_updates.return_value = [
            {
                "update_id": 100,
                "message": {
                    "chat": {"id": "12345"},
                    "text": "/help",
                },
            }
        ]
        config = {
            "telegram-api-token": "dummy_token",
            "telegram-chat-id": "12345",
        }
        with patch("InstaAddict.plugins.telegram._load_telegram_state", return_value={}), \
             patch("InstaAddict.plugins.telegram._save_telegram_state"):
            check_telegram_inbox(self.username, telegram_config=config, queue_dir=self.user_dir)
            mock_send_text.assert_called()
            call_text = mock_send_text.call_args[0][2]
            self.assertIn("/post", call_text)
            self.assertIn("/preview", call_text)
            self.assertIn("/cooldown", call_text)

    @patch("InstaAddict.plugins.telegram.telegram_bot_send_text")
    @patch("InstaAddict.plugins.telegram.telegram_bot_get_updates")
    def test_check_telegram_inbox_post_empty_queue(self, mock_updates, mock_send_text):
        mock_updates.return_value = [
            {
                "update_id": 101,
                "message": {
                    "chat": {"id": "12345"},
                    "text": "/post",
                },
            }
        ]
        config = {
            "telegram-api-token": "dummy_token",
            "telegram-chat-id": "12345",
        }
        with patch("InstaAddict.plugins.telegram._load_telegram_state", return_value={}), \
             patch("InstaAddict.plugins.telegram._save_telegram_state"):
            check_telegram_inbox(self.username, telegram_config=config, queue_dir=os.path.join(self.user_dir, "content_queue"))
            mock_send_text.assert_called()
            call_text = mock_send_text.call_args[0][2]
            self.assertIn("empty", call_text.lower())

    @patch("InstaAddict.plugins.telegram.trigger_on_demand_upload", return_value=True)
    @patch("InstaAddict.plugins.telegram.telegram_bot_send_text")
    @patch("InstaAddict.plugins.telegram.telegram_bot_get_updates")
    def test_check_telegram_inbox_post_force(self, mock_updates, mock_send_text, mock_trigger):
        # Place a dummy pending media file
        dummy_media = os.path.join(self.pending_dir, "test_item.jpg")
        with open(dummy_media, "w") as f:
            f.write("image")

        mock_updates.return_value = [
            {
                "update_id": 102,
                "message": {
                    "chat": {"id": "12345"},
                    "text": "/post_force",
                },
            }
        ]
        config = {
            "telegram-api-token": "dummy_token",
            "telegram-chat-id": "12345",
        }
        with patch("InstaAddict.plugins.telegram._load_telegram_state", return_value={}), \
             patch("InstaAddict.plugins.telegram._save_telegram_state"):
            check_telegram_inbox(self.username, telegram_config=config, queue_dir=os.path.join(self.user_dir, "content_queue"))
            mock_trigger.assert_called_with(
                self.username, force=True, token="dummy_token", auth_chat_id="12345"
            )
            mock_send_text.assert_called()
            call_text = mock_send_text.call_args[0][2]
            self.assertIn("Starting On-Demand Instagram Upload", call_text)

    @patch("InstaAddict.plugins.telegram.telegram_bot_send_photo", return_value={"ok": True})
    @patch("InstaAddict.plugins.telegram.telegram_bot_get_updates")
    def test_check_telegram_inbox_preview(self, mock_updates, mock_send_photo):
        dummy_media = os.path.join(self.pending_dir, "preview_item.jpg")
        dummy_txt = os.path.join(self.pending_dir, "preview_item.txt")
        with open(dummy_media, "w") as f:
            f.write("image")
        with open(dummy_txt, "w", encoding="utf-8") as f:
            f.write("Beautiful sunny day in the park! #sunny #doglife")

        mock_updates.return_value = [
            {
                "update_id": 103,
                "message": {
                    "chat": {"id": "12345"},
                    "text": "/preview",
                },
            }
        ]
        config = {
            "telegram-api-token": "dummy_token",
            "telegram-chat-id": "12345",
        }
        with patch("InstaAddict.plugins.telegram._load_telegram_state", return_value={}), \
             patch("InstaAddict.plugins.telegram._save_telegram_state"):
            check_telegram_inbox(self.username, telegram_config=config, queue_dir=os.path.join(self.user_dir, "content_queue"))
            mock_send_photo.assert_called()
            call_caption = mock_send_photo.call_args[1].get("caption", "")
            self.assertIn("Beautiful sunny day", call_caption)


if __name__ == "__main__":
    unittest.main()

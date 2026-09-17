import json
import os
import pytest
from unittest.mock import patch

from InstaAddict.plugins.telegram import (
    check_telegram_inbox,
    telegram_notify_upload_success,
)


@pytest.fixture
def temp_telegram_env(tmp_path):
    """Creates a temporary account queue environment for testing."""
    username = "testuser"
    account_dir = tmp_path / "accounts" / username
    pending_dir = account_dir / "content_queue" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "telegram-api-token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        "telegram-chat-id": "999888777",
    }
    with open(account_dir / "telegram.yml", "w", encoding="utf-8") as f:
        import yaml
        yaml.safe_dump(config, f)

    # Save initial state
    with open(account_dir / "telegram_state.json", "w", encoding="utf-8") as f:
        json.dump({"last_update_id": 100}, f)

    orig_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield {
        "username": username,
        "account_dir": str(account_dir),
        "pending_dir": str(pending_dir),
        "config": config,
        "tmp_path": tmp_path,
    }
    os.chdir(orig_cwd)


class TestTelegramCompanionComments:
    """Validates companion text comment binding, caption editing, and AI elaboration commands."""

    @patch("InstaAddict.plugins.telegram.telegram_bot_send_text")
    @patch("InstaAddict.plugins.telegram.telegram_bot_get_updates")
    def test_companion_comment_binds_to_recent_media(
        self, mock_updates, mock_send, temp_telegram_env
    ):
        username = temp_telegram_env["username"]
        pending_dir = temp_telegram_env["pending_dir"]

        # Create a pending image file with no .txt sidecar
        media_file = os.path.join(pending_dir, "20260915_120000_abc123.jpg")
        with open(media_file, "wb") as f:
            f.write(b"fake image data")

        # Simulate follow-up plain text message in Telegram
        mock_updates.return_value = [
            {
                "update_id": 101,
                "message": {
                    "chat": {"id": "999888777"},
                    "text": "Running through the waves at sunset! #beachvibes",
                },
            }
        ]

        count = check_telegram_inbox(username, telegram_config=temp_telegram_env["config"])
        assert count == 0  # No new media files queued, but companion comment processed

        # Verify that .txt sidecar was created with the companion comment
        sidecar_path = os.path.join(pending_dir, "20260915_120000_abc123.txt")
        assert os.path.exists(sidecar_path)
        with open(sidecar_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        assert content == "Running through the waves at sunset! #beachvibes"

        # Verify confirmation was sent to Telegram
        mock_send.assert_called()
        args, _ = mock_send.call_args
        assert "Companion Comment Attached!" in args[2]
        assert "20260915_120000_abc123.jpg" in args[2]

    @patch("InstaAddict.plugins.telegram.telegram_bot_send_text")
    @patch("InstaAddict.plugins.telegram.telegram_bot_get_updates")
    def test_caption_command_overrides_pending_sidecar(
        self, mock_updates, mock_send, temp_telegram_env
    ):
        username = temp_telegram_env["username"]
        pending_dir = temp_telegram_env["pending_dir"]

        media_file = os.path.join(pending_dir, "test_post.jpg")
        with open(media_file, "wb") as f:
            f.write(b"fake image data")

        mock_updates.return_value = [
            {
                "update_id": 102,
                "message": {
                    "chat": {"id": "999888777"},
                    "text": "/caption Custom manually edited caption from Telegram!",
                },
            }
        ]

        check_telegram_inbox(username, telegram_config=temp_telegram_env["config"])

        sidecar_path = os.path.join(pending_dir, "test_post.txt")
        assert os.path.exists(sidecar_path)
        with open(sidecar_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        assert content == "Custom manually edited caption from Telegram!"

        mock_send.assert_called()
        args, _ = mock_send.call_args
        assert "Caption Updated!" in args[2]

    @patch("InstaAddict.core.gemini_vision.get_vision_caption")
    @patch("InstaAddict.plugins.telegram.telegram_bot_send_text")
    @patch("InstaAddict.plugins.telegram.telegram_bot_get_updates")
    def test_elaborate_command_triggers_ai_generation(
        self, mock_updates, mock_send, mock_vision_caption, temp_telegram_env
    ):
        username = temp_telegram_env["username"]
        pending_dir = temp_telegram_env["pending_dir"]

        media_file = os.path.join(pending_dir, "test_post.jpg")
        with open(media_file, "wb") as f:
            f.write(b"fake image data")

        mock_vision_caption.return_value = "Golden hour walks in the sunshine! #nature #sunshine #adventure"

        mock_updates.return_value = [
            {
                "update_id": 103,
                "message": {
                    "chat": {"id": "999888777"},
                    "text": "/elaborate",
                },
            }
        ]

        check_telegram_inbox(username, telegram_config=temp_telegram_env["config"])

        sidecar_path = os.path.join(pending_dir, "test_post.txt")
        assert os.path.exists(sidecar_path)
        with open(sidecar_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        assert content == "Golden hour walks in the sunshine! #nature #sunshine #adventure"

    @patch("InstaAddict.plugins.telegram.telegram_bot_send_text")
    def test_telegram_notify_upload_success(self, mock_send, temp_telegram_env):
        username = temp_telegram_env["username"]
        mock_send.return_value = {"ok": True}

        success = telegram_notify_upload_success(
            username=username,
            media_file="post_1.jpg",
            caption="Morning coffee and fresh air! #morning #goodvibes",
            telegram_config=temp_telegram_env["config"],
        )
        assert success is True
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert "Instagram Post Published!" in args[2]
        assert "post_1.jpg" in args[2]

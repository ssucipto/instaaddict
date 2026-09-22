import os
from unittest.mock import MagicMock, patch

import pytest

from InstaAddict.plugins.telegram import (
    _load_telegram_state,
    _save_telegram_state,
    check_telegram_inbox,
)


@pytest.fixture
def temp_account_dir(tmp_path):
    """Sets up a temporary account directory with telegram configuration and content queue."""
    username = "test_user"
    acct_dir = tmp_path / "accounts" / username
    acct_dir.mkdir(parents=True)
    queue_dir = acct_dir / "content_queue"
    pending_dir = queue_dir / "pending"
    pending_dir.mkdir(parents=True)

    config_content = (
        "telegram-api-token: 123456:TEST_TOKEN\n"
        "telegram-chat-id: '99887766'\n"
    )
    (acct_dir / "telegram.yml").write_text(config_content, encoding="utf-8")

    cwd = os.getcwd()
    os.chdir(tmp_path)
    yield username, str(queue_dir), str(pending_dir)
    os.chdir(cwd)


def test_telegram_state_load_save(temp_account_dir):
    username, _, _ = temp_account_dir
    state = _load_telegram_state(username)
    assert state == {}

    _save_telegram_state(username, {"last_update_id": 1005})
    loaded = _load_telegram_state(username)
    assert loaded.get("last_update_id") == 1005


def test_telegram_inbox_authorizes_correct_chat_id(temp_account_dir):
    username, queue_dir, pending_dir = temp_account_dir

    mock_updates = [
        {
            "update_id": 1,
            "message": {
                "chat": {"id": 111111},  # Unauthorized
                "text": "Hello bot",
            },
        },
        {
            "update_id": 2,
            "message": {
                "chat": {"id": 99887766},  # Authorized
                "text": "/help",
            },
        },
    ]

    with patch("InstaAddict.plugins.telegram.telegram_bot_get_updates", return_value=mock_updates), \
         patch("InstaAddict.plugins.telegram.telegram_bot_send_text") as mock_send_text:
        queued = check_telegram_inbox(username, queue_dir=queue_dir)
        assert queued == 0
        # Only authorized message got a reply
        assert mock_send_text.call_count == 1
        args, _ = mock_send_text.call_args
        assert args[1] == "99887766"
        assert "InstaAddict-AI Telegram Assistant" in args[2]


def test_telegram_inbox_photo_download_and_caption_sidecar(temp_account_dir):
    username, queue_dir, pending_dir = temp_account_dir

    mock_updates = [
        {
            "update_id": 10,
            "message": {
                "chat": {"id": 99887766},
                "photo": [
                    {"file_id": "thumb_id", "file_size": 100},
                    {"file_id": "full_photo_id", "file_size": 5000},
                ],
                "caption": "Enjoying the morning sunshine! #photography #nature",
            },
        }
    ]

    def mock_download(token, file_path, dest_path):
        with open(dest_path, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIFdummyimagebytes")
        return True

    with patch("InstaAddict.plugins.telegram.telegram_bot_get_updates", return_value=mock_updates), \
         patch("InstaAddict.plugins.telegram.telegram_bot_get_file_path", return_value="photos/file_1.jpg"), \
         patch("InstaAddict.plugins.telegram.telegram_bot_download_file", side_effect=mock_download), \
         patch("InstaAddict.plugins.telegram.telegram_bot_send_text") as mock_send_text:
        queued = check_telegram_inbox(username, queue_dir=queue_dir)
        assert queued == 1

        # Check pending directory files
        pending_files = os.listdir(pending_dir)
        media_files = [f for f in pending_files if f.endswith(".jpg")]
        txt_files = [f for f in pending_files if f.endswith(".txt")]

        assert len(media_files) == 1
        assert len(txt_files) == 1

        # Check caption content
        txt_path = os.path.join(pending_dir, txt_files[0])
        with open(txt_path, "r", encoding="utf-8") as f:
            assert f.read() == "Enjoying the morning sunshine! #photography #nature"

        # Check receipt message sent
        assert mock_send_text.call_count == 1
        receipt_text = mock_send_text.call_args[0][2]
        assert "Media Queued for Upload!" in receipt_text
        assert "#1" in receipt_text


def test_telegram_inbox_queue_and_status_commands(temp_account_dir):
    username, queue_dir, pending_dir = temp_account_dir

    # Create dummy queued post
    dummy_img = os.path.join(pending_dir, "20260914_001.jpg")
    dummy_txt = os.path.join(pending_dir, "20260914_001.txt")
    with open(dummy_img, "wb") as f:
        f.write(b"dummy")
    with open(dummy_txt, "w", encoding="utf-8") as f:
        f.write("A test caption for queue inspection")

    mock_updates = [
        {
            "update_id": 20,
            "message": {
                "chat": {"id": 99887766},
                "text": "/queue",
            },
        },
        {
            "update_id": 21,
            "message": {
                "chat": {"id": 99887766},
                "text": "/status",
            },
        },
    ]

    with patch("InstaAddict.plugins.telegram.telegram_bot_get_updates", return_value=mock_updates), \
         patch("InstaAddict.plugins.telegram.telegram_bot_send_text") as mock_send_text:
        queued = check_telegram_inbox(username, queue_dir=queue_dir)
        assert queued == 0
        assert mock_send_text.call_count == 2

        queue_call = mock_send_text.call_args_list[0][0][2]
        status_call = mock_send_text.call_args_list[1][0][2]

        assert "Pending Upload Queue" in queue_call
        assert "20260914_001.jpg" in queue_call
        assert "A test caption" in queue_call

        assert "InstaAddict-AI Bot Status" in status_call
        assert "1 pending" in status_call


def test_upload_posts_sends_telegram_notification(temp_account_dir):
    """Verify that UploadPostsPlugin sends a telegram message when upload succeeds."""
    from InstaAddict.plugins.upload_posts import UploadPostsPlugin

    username, queue_dir, pending_dir = temp_account_dir
    published_dir = os.path.join(queue_dir, "published")
    os.makedirs(published_dir, exist_ok=True)

    # Put a test image in pending
    media_file = "test_media.jpg"
    media_path = os.path.join(pending_dir, media_file)
    with open(media_path, "wb") as f:
        f.write(b"fake_jpg")

    txt_path = os.path.join(pending_dir, "test_media.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Awesome day in the park!")

    plugin = UploadPostsPlugin()
    mock_configs = MagicMock()
    mock_configs.args.upload_queue_dir = queue_dir
    mock_configs.args.username = username
    mock_configs.args.config = os.path.join("accounts", username, "config.yml")
    mock_device = MagicMock()
    mock_storage = MagicMock()

    with patch.object(plugin, "_upload_to_ig", return_value=True), \
         patch("InstaAddict.plugins.upload_posts.get_vision_caption", return_value=""), \
         patch("InstaAddict.plugins.telegram.telegram_bot_send_text") as mock_send_tg:
        plugin.run(
            device=mock_device,
            configs=mock_configs,
            storage=mock_storage,
            sessions=[MagicMock()],
            profile_filter=MagicMock(),
            plugin=plugin,
        )

        assert mock_send_tg.call_count == 1
        tg_text = mock_send_tg.call_args[0][2]
        assert "Instagram Post Published!" in tg_text
        assert "test_media.jpg" in tg_text
        assert "Awesome day in the park!" in tg_text


def test_telegram_inbox_argument_not_an_operation():
    """Verify --telegram-inbox is NOT marked as an operation."""
    from InstaAddict.plugins.telegram import TelegramReports

    plugin = TelegramReports()
    inbox_arg = next(
        (a for a in plugin.arguments if a.get("arg") == "--telegram-inbox"),
        None,
    )
    assert inbox_arg is not None
    assert inbox_arg.get("operation", False) is False

    reports_arg = next(
        (a for a in plugin.arguments if a.get("arg") == "--telegram-reports"),
        None,
    )
    assert reports_arg is not None
    assert reports_arg.get("operation", False) is True


def test_telegram_reports_run_resilient_to_operational_dispatch():
    """Verify TelegramReports.run tolerates standard operational invocation."""
    from InstaAddict.plugins.telegram import TelegramReports

    plugin = TelegramReports()
    mock_device = MagicMock()
    mock_configs = MagicMock()
    mock_configs.args.username = "test_user"
    mock_storage = MagicMock()
    mock_sessions = [MagicMock()]
    mock_filters = MagicMock()

    # Standard operational plugin call: run(dev, cfg, stor, sess, filt, plug)
    # Must not raise TypeError
    plugin.run(
        mock_device,
        mock_configs,
        mock_storage,
        mock_sessions,
        mock_filters,
        "telegram-inbox",
    )


def test_uncaught_exception_stops_tui_and_calls_excepthook():
    """Verify handle_uncaught_exception stops TUI and calls excepthook."""
    import sys
    import InstaAddict.core.log as log_module

    mock_mgr = MagicMock()
    with patch("InstaAddict.core.tui.DashboardManager.is_active",
               return_value=True), \
         patch("InstaAddict.core.tui.DashboardManager.get_instance",
               return_value=mock_mgr), \
         patch("InstaAddict.core.log.disable_tui_logging") as mock_disable_tui, \
         patch.object(sys, "__excepthook__") as mock_orig_excepthook:

        # Re-initialize logging or directly test sys.excepthook
        log_module.configure_logger(debug=False, username="test_user")
        excepthook = sys.excepthook

        test_exc = TypeError("TelegramReports.run() takes 6 positional args")
        excepthook(TypeError, test_exc, None)

        mock_mgr.stop.assert_called_once()
        mock_disable_tui.assert_called_once()
        mock_orig_excepthook.assert_called_once_with(TypeError, test_exc, None)


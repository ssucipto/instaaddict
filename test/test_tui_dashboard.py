import logging
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, PropertyMock, patch

from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

from InstaAddict.core.log import (
    disable_tui_logging,
    enable_tui_logging,
)
from InstaAddict.core.tui import (
    DashboardManager,
    DashboardState,
    KeyboardListenerThread,
    TuiLogHandler,
    _safe_int,
    safe_glyph,
)


class TestHelpers:
    def test_safe_int(self):
        assert _safe_int(42, 10) == 42
        assert _safe_int("100", 10) == 100
        assert _safe_int(None, 10) == 10
        assert _safe_int("invalid", 10) == 10
        assert _safe_int([], 10) == 10

    def test_safe_glyph(self):
        # Under UTF-8 encoding
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        with patch("sys.stdout", mock_stdout):
            assert safe_glyph("🤖", "[*]") == "🤖"

        # Under CP1252 encoding
        mock_stdout_cp = MagicMock()
        mock_stdout_cp.encoding = "cp1252"
        with patch("sys.stdout", mock_stdout_cp):
            assert safe_glyph("🤖", "[*]") == "[*]"
            assert safe_glyph("📱", "[Dev]") == "[Dev]"
            assert safe_glyph("⏱️", "[Time]") == "[Time]"


class TestDashboardState:
    def test_default_state(self):
        state = DashboardState()
        assert state.username is None
        assert state.device_status == "Connected"
        assert state.status_message == "RUNNING"
        assert state.likes_count == 0
        assert state.likes_limit == 300
        assert state.crashes_count == 0
        assert state.total_interactions == 0
        assert len(state.logs_buffer) == 0

    def test_elapsed_duration_str(self):
        state = DashboardState()
        state.start_time = datetime.now() - timedelta(seconds=125)
        duration_str = state.elapsed_duration_str()
        assert "0:02:05" in duration_str or "02:05" in duration_str

    def test_update_countdown(self):
        state = DashboardState()
        state.update_countdown(15, "Waiting for cooldown...")
        assert state.countdown_seconds == 15
        assert state.countdown_message == "Waiting for cooldown..."

        state.update_countdown(None, "")
        assert state.countdown_seconds is None
        assert state.countdown_message == ""

    def test_update_from_session_state(self):
        state = DashboardState()
        mock_ss = MagicMock()
        mock_ss.totalLikes = 42
        mock_ss.totalFollowed = {"hashtag": 10, "feed": 5}
        mock_ss.totalUnfollowed = 8
        mock_ss.totalComments = 4
        mock_ss.totalWatched = 20
        mock_ss.totalCrashes = 1
        mock_ss.totalInteractions = {"likes": 42, "follows": 15}
        mock_ss.totalUploadsSuccess = 2
        mock_ss.totalUploadsFailed = 0

        mock_ss.args.current_likes_limit = 100
        mock_ss.args.current_follow_limit = 50
        mock_ss.args.current_unfollow_limit = 40
        mock_ss.args.current_comments_limit = 15
        mock_ss.args.current_watch_limit = 60
        mock_ss.args.current_crashes_limit = 5
        mock_ss.args.current_total_limit = 500

        state.update_from_session_state(mock_ss)

        assert state.likes_count == 42
        assert state.likes_limit == 100
        assert state.follows_count == 15
        assert state.unfollows_count == 8
        assert state.comments_count == 4
        assert state.watched_count == 20
        assert state.crashes_count == 1
        assert state.total_interactions == 57
        assert state.uploads_ok == 2
        assert state.uploads_fail == 0

    def test_update_from_session_state_with_partial_none(self):
        state = DashboardState()
        mock_ss = MagicMock()
        mock_ss.totalLikes = 10
        mock_ss.totalFollowed = {}
        mock_ss.totalInteractions = {}
        # Simulate partial None in limits
        mock_ss.args.current_likes_limit = None
        mock_ss.args.current_follow_limit = 25
        mock_ss.args.current_unfollow_limit = "invalid"
        mock_ss.args.current_comments_limit = None
        mock_ss.args.current_watch_limit = 80
        mock_ss.args.current_crashes_limit = None
        mock_ss.args.current_total_limit = None

        state.update_from_session_state(mock_ss)

        # Unaffected limits should keep defaults
        assert state.likes_limit == 300
        assert state.follows_limit == 25
        assert state.unfollows_limit == 50
        assert state.watched_limit == 80

    def test_logs_buffer_maxlen(self):
        state = DashboardState()
        for i in range(40):
            state.logs_buffer.append(("INFO", "12:00:00", f"Message {i}"))
        assert len(state.logs_buffer) == 30
        assert state.logs_buffer[0][2] == "Message 10"
        assert state.logs_buffer[-1][2] == "Message 39"

    def test_effort_counters_and_session_sync(self):
        state = DashboardState()
        mock_ss = MagicMock()
        mock_ss.my_username = "non_existent_mock_user"
        mock_ss.totalLikes = 5
        mock_ss.totalFollowed = {}
        mock_ss.totalInteractions = {}
        mock_ss.totalPostsChecked = 45
        mock_ss.totalProfilesChecked = 20
        mock_ss.totalProfilesSkipped = 15
        mock_ss.totalAdsBypassed = 6
        mock_ss.totalDialogsDismissed = 3
        mock_ss.totalReelsEvaluated = 12
        mock_ss.uploadHistory = [{"timestamp": (datetime.now() - timedelta(minutes=25)).isoformat()}]
        mock_ss.args = None

        state.update_from_session_state(mock_ss)

        assert state.posts_checked == 45
        assert state.profiles_checked == 20
        assert state.profiles_skipped == 15
        assert state.ads_bypassed == 6
        assert state.dialogs_dismissed == 3
        assert state.reels_evaluated == 12
        assert "25m ago" in state.last_upload_time_str or "Just now" in state.last_upload_time_str

    def test_consume_upload_request(self):
        state = DashboardState()
        assert state.consume_upload_request() is False
        state.trigger_upload()
        assert state.upload_requested is True
        assert state.consume_upload_request() is True
        assert state.upload_requested is False
        assert state.consume_upload_request() is False

    def test_consume_skip_task_request(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state = DashboardState()
        state.username = "bob"
        assert state.consume_skip_task_request() is False
        assert state.is_skip_task_requested() is False

        # Test memory flag
        state.trigger_skip_task()
        assert state.skip_task_requested is True
        assert state.is_skip_task_requested() is True
        assert state.consume_skip_task_request() is True
        assert state.skip_task_requested is False
        assert state.consume_skip_task_request() is False

        # Test IPC signal file
        signal_dir = tmp_path / "accounts" / "bob"
        signal_dir.mkdir(parents=True)
        signal_file = signal_dir / ".skip_task"
        signal_file.write_text("skip")

        assert state.is_skip_task_requested() is True
        assert state.consume_skip_task_request() is True
        assert not signal_file.exists()
        assert state.consume_skip_task_request() is False

    def test_refresh_queue_status_with_temp_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state = DashboardState()
        user_pending = tmp_path / "accounts" / "alice" / "content_queue" / "pending"
        user_pending.mkdir(parents=True)
        (user_pending / "img1.jpg").write_bytes(b"mock")
        (user_pending / "img2.PNG").write_bytes(b"mock")
        (user_pending / "clip.mp4").write_bytes(b"mock")
        (user_pending / "notes.txt").write_text("caption notes")

        user_published = tmp_path / "accounts" / "alice" / "content_queue" / "published"
        user_published.mkdir(parents=True)
        (user_published / "done1.jpg").write_bytes(b"mock")

        state.refresh_queue_status(username="alice")

        assert state.queue_pending == 3
        assert state.queue_published == 1
        assert "Just now" in state.last_upload_time_str or "m ago" in state.last_upload_time_str


class TestTuiLogHandler:
    def test_emit_adds_to_buffer(self):
        state = DashboardState()
        handler = TuiLogHandler(state)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        logger = logging.getLogger("test_tui_logger")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        logger.info("Test hello world log entry")

        assert len(state.logs_buffer) == 1
        level_name, time_str, msg = state.logs_buffer[0]
        assert level_name == "INFO"
        assert "Test hello world log entry" in msg

        logger.removeHandler(handler)

    def test_ansi_escape_cleaned(self):
        state = DashboardState()
        handler = TuiLogHandler(state)
        logger = logging.getLogger("test_ansi_logger")
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        # Message with ANSI color codes
        logger.warning("\x1b[31;1mWarning with ANSI colors\x1b[0m")

        assert len(state.logs_buffer) == 1
        level_name, _, msg = state.logs_buffer[0]
        assert level_name == "WARNING"
        assert "\x1b[" not in msg
        assert "Warning with ANSI colors" in msg

        logger.removeHandler(handler)

    def test_multiline_log_split(self):
        state = DashboardState()
        handler = TuiLogHandler(state)
        logger = logging.getLogger("test_multiline_logger")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        logger.info("Line 1\nLine 2\nLine 3")

        assert len(state.logs_buffer) == 3
        assert state.logs_buffer[0][2] == "Line 1"
        assert state.logs_buffer[1][2] == "Line 2"
        assert state.logs_buffer[2][2] == "Line 3"

        logger.removeHandler(handler)


class TestDashboardManager:
    def test_singleton_pattern(self):
        m1 = DashboardManager.get_instance()
        m2 = DashboardManager.get_instance()
        assert m1 is m2

    def test_layout_generation(self):
        mgr = DashboardManager.get_instance()
        mgr.state.username = "test_user"
        mgr.state.likes_count = 50
        mgr.state.likes_limit = 100
        mgr.state.crashes_count = 1

        layout = mgr.generate_layout()
        assert isinstance(layout, Layout)
        # Check sub-elements render properly
        header = mgr._render_header()
        assert isinstance(header, Panel)
        stats = mgr._render_stats_table()
        assert isinstance(stats, (Table, Group))
        activity = mgr._render_activity_panel()
        assert isinstance(activity, Panel)
        logs = mgr._render_logs_panel()
        assert isinstance(logs, Panel)
        footer = mgr._render_footer()
        assert isinstance(footer, Panel)
        plain_footer = getattr(footer.renderable, "renderable", footer.renderable).plain
        assert "[Ctrl+U]" in plain_footer
        assert "Upload Queued Photo" in plain_footer
        assert "[Ctrl+S]" in plain_footer
        assert "Skip Task" in plain_footer
        assert "[Ctrl+D]" in plain_footer

    def test_keyboard_listener_keys(self):
        mgr = DashboardManager.get_instance()
        listener = KeyboardListenerThread(mgr)

        with patch.object(mgr, "trigger_upload_request") as mock_upload, \
             patch.object(mgr, "trigger_debug_toggle") as mock_debug, \
             patch.object(mgr, "trigger_skip_task") as mock_skip:
            # Letter fallbacks
            listener._handle_key("u")
            mock_upload.assert_called_once()
            listener._handle_key("d")
            mock_debug.assert_called_once()
            listener._handle_key("s")
            assert mock_skip.call_count == 1
            listener._handle_key("n")
            assert mock_skip.call_count == 2

            # Control characters (bytes and str)
            listener._handle_key(b"\x15")  # Ctrl+U
            assert mock_upload.call_count == 2
            listener._handle_key("\x15")   # Ctrl+U str
            assert mock_upload.call_count == 3

            listener._handle_key(b"\x04")  # Ctrl+D
            assert mock_debug.call_count == 2
            listener._handle_key("\x04")   # Ctrl+D str
            assert mock_debug.call_count == 3

            listener._handle_key(b"\x13")  # Ctrl+S
            assert mock_skip.call_count == 3
            listener._handle_key("\x13")   # Ctrl+S str
            assert mock_skip.call_count == 4

    def test_keyboard_listener_non_tty_graceful_exit(self):
        mgr = DashboardManager.get_instance()
        listener = KeyboardListenerThread(mgr)
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        with patch("sys.stdin", mock_stdin):
            listener.run()

    def test_responsive_layout_width(self):
        mgr = DashboardManager.get_instance()
        # Narrow width (< 85)
        with patch.object(Console, "width", new=PropertyMock(return_value=70)):
            layout_narrow = mgr.generate_layout()
            assert isinstance(layout_narrow, Layout)

        # Wide width (>= 85)
        with patch.object(Console, "width", new=PropertyMock(return_value=120)):
            layout_wide = mgr.generate_layout()
            assert isinstance(layout_wide, Layout)

    def test_start_stop_mocked(self):
        mgr = DashboardManager.get_instance()
        with patch("rich.live.Live.start"), patch("rich.live.Live.stop"):
            mgr.start()
            assert mgr.is_active() is True
            assert mgr.live is not None
            # Verify zero-flicker parameters
            assert mgr.live._screen is True
            assert mgr.live.vertical_overflow == "crop"
            mgr.update_render()
            mgr.stop()
            assert mgr.is_active() is False

    def test_logs_panel_slicing_by_console_height(self):
        mgr = DashboardManager.get_instance()
        for i in range(30):
            mgr.state.add_log("INFO", "12:00:00", f"Log line {i}")
        assert len(mgr.state.logs_buffer) == 30

        # On standard 25-line console, logs panel should slice to avoid vertical overflow
        with patch.object(Console, "height", new=PropertyMock(return_value=25)), \
             patch.object(Console, "width", new=PropertyMock(return_value=100)):
            panel = mgr._render_logs_panel()
            assert isinstance(panel, Panel)
            # Panel text should only have the sliced count + 1 newline per entry
            text_lines = [line for line in panel.renderable.plain.splitlines() if line.strip()]
            assert len(text_lines) < 30
            assert len(text_lines) == 17  # 25 - 8 = 17

    def test_update_render_throttling(self):
        mgr = DashboardManager.get_instance()
        with patch("rich.live.Live.start"), patch("rich.live.Live.stop"), patch("rich.live.Live.update") as mock_update:
            mgr.start()
            mgr._last_render_time = time.time()
            # Rapid call within 0.5s should be throttled
            mgr.update_render(force=False)
            assert mock_update.call_count == 0

            # Forced call should bypass throttle
            mgr.update_render(force=True)
            assert mock_update.call_count == 1
            mgr.stop()

    def test_context_manager_mocked(self):
        mgr = DashboardManager.get_instance()
        with patch("rich.live.Live.start"), patch("rich.live.Live.stop"):
            with mgr:
                assert mgr.is_active() is True
            assert mgr.is_active() is False

    def test_enable_and_disable_tui_logging(self):
        mgr = DashboardManager.get_instance()
        root_logger = logging.getLogger()

        enable_tui_logging(mgr)
        root_handlers = root_logger.handlers
        assert any(isinstance(h, TuiLogHandler) for h in root_handlers)

        disable_tui_logging()
        root_handlers = root_logger.handlers
        assert not any(isinstance(h, TuiLogHandler) for h in root_handlers)


class TestArgumentParsing:
    def test_tui_flags(self):
        from InstaAddict.core.config import Config

        config = Config()
        config.load_plugins()

        # Parse with --tui
        args = config.parser.parse_args(["--tui"])
        assert args.tui is True
        assert args.no_tui is False

        # Parse with --no-tui
        config2 = Config()
        config2.load_plugins()
        args2 = config2.parser.parse_args(["--no-tui"])
        assert args2.no_tui is True
        assert args2.tui is False

    def test_countdown_skip_task(self):
        from InstaAddict.core.utils import countdown

        mgr = DashboardManager.get_instance()
        with patch.object(DashboardManager, "is_active", return_value=True):
            # Pre-arm skip task request
            mgr.state.skip_task_requested = True
            start_time = time.time()
            # Countdown of 10 seconds should exit instantly
            countdown(10, "Waiting: ")
            elapsed = time.time() - start_time
            assert elapsed < 2.0
            assert mgr.state.skip_task_requested is False

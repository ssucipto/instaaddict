import atexit
import logging
import os
import re
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Deque, Optional, Tuple

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from InstaAddict import __version__


def safe_glyph(glyph: str, fallback: str) -> str:
    """Return emoji glyph if current stdout encoding supports it, else return safe ascii fallback."""
    encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
    if "utf" not in encoding.lower():
        return fallback
    try:
        glyph.encode(encoding, errors="strict")
        return glyph
    except Exception:
        return fallback


def _safe_int(val, default: int) -> int:
    """Safely parse integer value or return default without throwing."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


@dataclass
class DashboardState:
    """Thread-safe state container for TUI dashboard metrics and display data."""

    # Account metadata
    username: Optional[str] = None
    followers_count: Optional[str] = None
    following_count: Optional[str] = None
    posts_count: Optional[str] = None

    # Device metadata
    device_id: Optional[str] = None
    device_model: Optional[str] = None
    device_status: str = "Connected"

    # Session metadata
    session_index: int = 1
    total_sessions: int = 1
    start_time: datetime = field(default_factory=datetime.now)
    status_message: str = "RUNNING"
    working_hours_status: str = "Active"

    # Activity & context
    current_job: str = "Initializing..."
    current_action: str = "Starting bot engine..."
    target_user: Optional[str] = None
    target_source: Optional[str] = None
    countdown_seconds: Optional[int] = None
    countdown_message: str = ""

    # Interaction counts
    likes_count: int = 0
    likes_limit: int = 300
    follows_count: int = 0
    follows_limit: int = 50
    unfollows_count: int = 0
    unfollows_limit: int = 50
    comments_count: int = 0
    comments_limit: int = 10
    watched_count: int = 0
    watched_limit: int = 50
    uploads_ok: int = 0
    uploads_fail: int = 0
    crashes_count: int = 0
    crashes_limit: int = 5
    total_interactions: int = 0
    total_interactions_limit: int = 1000

    # Logs ring buffer
    logs_buffer: Deque[Tuple[str, str, str]] = field(
        default_factory=lambda: deque(maxlen=30)
    )

    # Pipeline & Effort counters (Live non-KPI operational metrics)
    posts_checked: int = 0
    profiles_checked: int = 0
    profiles_skipped: int = 0
    ads_bypassed: int = 0
    dialogs_dismissed: int = 0
    reels_evaluated: int = 0
    watchdog_recoveries: int = 0

    # Content queue & upload telemetry
    queue_pending: int = 0
    queue_published: int = 0
    last_upload_time_str: str = "Never"
    upload_cooldown_str: str = "Ready"
    upload_requested: bool = False
    skip_task_requested: bool = False

    # Concurrency guard
    lock: threading.RLock = field(default_factory=threading.RLock)

    def elapsed_duration_str(self) -> str:
        delta = datetime.now() - self.start_time
        return str(timedelta(seconds=int(delta.total_seconds())))

    def consume_upload_request(self) -> bool:
        """Atomically consume any pending manual upload request triggered via hotkey [U]."""
        with self.lock:
            if self.upload_requested:
                self.upload_requested = False
                return True
            return False

    def trigger_upload(self):
        """Flag manual upload requested."""
        with self.lock:
            self.upload_requested = True

    def is_upload_requested(self) -> bool:
        """Non-destructively check if manual upload is requested."""
        with self.lock:
            return bool(self.upload_requested)

    def consume_skip_task_request(self) -> bool:
        """Atomically consume any pending skip task request triggered via hotkey [S]/[N] or IPC file."""
        with self.lock:
            signal_file = None
            if self.username:
                signal_file = os.path.join("accounts", self.username, ".skip_task")
            if signal_file and os.path.isfile(signal_file):
                try:
                    os.remove(signal_file)
                    self.skip_task_requested = False
                    return True
                except Exception:
                    pass

            if self.skip_task_requested:
                self.skip_task_requested = False
                return True
            return False

    def trigger_skip_task(self):
        """Flag task skip requested."""
        with self.lock:
            self.skip_task_requested = True

    def is_skip_task_requested(self) -> bool:
        """Non-destructively check if skip task is requested."""
        with self.lock:
            if self.skip_task_requested:
                return True
            if self.username:
                signal_file = os.path.join("accounts", self.username, ".skip_task")
                if os.path.isfile(signal_file):
                    return True
            return False

    def refresh_queue_status(self, username: Optional[str] = None):
        """Scan content queue directory on disk and update queue telemetry."""
        with self.lock:
            user = username or self.username
            if not isinstance(user, str) or not user.strip():
                user = None

            pending_candidates = []
            if user:
                pending_candidates.extend([
                    os.path.join("accounts", user, "content_queue", "pending"),
                    os.path.join("accounts", user, "upload_queue", "pending"),
                ])
            else:
                # Fallback scan of any accounts directory or global upload_queue
                if os.path.isdir("accounts"):
                    try:
                        for d in os.listdir("accounts"):
                            p = os.path.join("accounts", d, "content_queue", "pending")
                            if os.path.isdir(p) and p not in pending_candidates:
                                pending_candidates.append(p)
                    except Exception:
                        pass
                pending_candidates.append("upload_queue/pending")

            allowed_exts = (".jpg", ".jpeg", ".png", ".mp4")
            pending_count = 0
            found_pending_dir = None
            for pdir in pending_candidates:
                if os.path.isdir(pdir):
                    found_pending_dir = pdir
                    try:
                        files = [f for f in os.listdir(pdir) if f.lower().endswith(allowed_exts)]
                        pending_count = len(files)
                        break
                    except Exception:
                        pass

            self.queue_pending = pending_count

            # Check published directory
            published_candidates = []
            if found_pending_dir:
                published_candidates.append(os.path.join(os.path.dirname(found_pending_dir), "published"))
            if user:
                published_candidates.append(os.path.join("accounts", user, "content_queue", "published"))
                published_candidates.append(os.path.join("accounts", user, "upload_queue", "published"))

            published_count = 0
            latest_mtime = None
            for pdir in published_candidates:
                if os.path.isdir(pdir):
                    try:
                        for root, _, files in os.walk(pdir):
                            for f in files:
                                if f.lower().endswith(allowed_exts):
                                    published_count += 1
                                    try:
                                        mt = datetime.fromtimestamp(os.path.getmtime(os.path.join(root, f)))
                                        if latest_mtime is None or mt > latest_mtime:
                                            latest_mtime = mt
                                    except Exception:
                                        pass
                        if published_count > 0:
                            break
                    except Exception:
                        pass

            self.queue_published = published_count

            # Determine last upload time string and cooldown
            if latest_mtime:
                delta = datetime.now() - latest_mtime
                secs = int(delta.total_seconds())
                if secs < 60:
                    self.last_upload_time_str = "Just now"
                elif secs < 3600:
                    self.last_upload_time_str = f"{secs // 60}m ago"
                elif secs < 86400:
                    self.last_upload_time_str = f"{secs // 3600}h {(secs % 3600) // 60}m ago"
                else:
                    self.last_upload_time_str = f"{secs // 86400}d ago"

                # Standard rate limit is 12 hours
                rate_limit_secs = 12 * 3600
                if secs < rate_limit_secs:
                    rem_secs = rate_limit_secs - secs
                    rem_h = rem_secs // 3600
                    rem_m = (rem_secs % 3600) // 60
                    self.upload_cooldown_str = f"{rem_h}h {rem_m}m"
                else:
                    self.upload_cooldown_str = "Ready"
            elif self.last_upload_time_str != "Never":
                self.upload_cooldown_str = "Ready"
            else:
                self.upload_cooldown_str = "Ready"

    def update_account(
        self,
        username: Optional[str] = None,
        followers: Optional[str] = None,
        following: Optional[str] = None,
        posts: Optional[str] = None,
    ):
        with self.lock:
            if username:
                self.username = username
            if followers is not None:
                self.followers_count = str(followers)
            if following is not None:
                self.following_count = str(following)
            if posts is not None:
                self.posts_count = str(posts)

    def update_activity(
        self,
        job: Optional[str] = None,
        action: Optional[str] = None,
        target: Optional[str] = None,
        source: Optional[str] = None,
    ):
        with self.lock:
            if job is not None:
                self.current_job = job
            if action is not None:
                self.current_action = action
            if target is not None:
                self.target_user = target
            if source is not None:
                self.target_source = source

        from InstaAddict.core.watchdog import record_heartbeat

        record_heartbeat(stage=self.current_job, action=self.current_action)

    def update_countdown(self, seconds: Optional[int], message: str = ""):
        with self.lock:
            self.countdown_seconds = seconds
            self.countdown_message = message

    def add_log(self, level: str, timestamp: str, message: str):
        with self.lock:
            self.logs_buffer.append((level, timestamp, message))

    def update_from_session_state(self, session):
        """Sync metrics and limits from a SessionState instance."""
        if not session:
            return
        with self.lock:
            if getattr(session, "my_username", None):
                self.username = session.my_username
            if getattr(session, "my_followers_count", None) is not None:
                self.followers_count = str(session.my_followers_count)
            if getattr(session, "my_following_count", None) is not None:
                self.following_count = str(session.my_following_count)
            if getattr(session, "my_posts_count", None) is not None:
                self.posts_count = str(session.my_posts_count)

            self.likes_count = getattr(session, "totalLikes", 0)
            self.follows_count = sum(getattr(session, "totalFollowed", {}).values())
            self.unfollows_count = getattr(session, "totalUnfollowed", 0)
            self.comments_count = getattr(session, "totalComments", 0)
            self.watched_count = getattr(session, "totalWatched", 0)
            self.uploads_ok = getattr(session, "totalUploadsSuccess", 0)
            self.uploads_fail = getattr(session, "totalUploadsFailed", 0)
            self.crashes_count = getattr(session, "totalCrashes", 0)
            self.total_interactions = sum(
                getattr(session, "totalInteractions", {}).values()
            )

            # Live effort counters
            self.posts_checked = getattr(session, "totalPostsChecked", 0)
            self.profiles_checked = getattr(session, "totalProfilesChecked", 0)
            self.profiles_skipped = getattr(session, "totalProfilesSkipped", 0)
            self.ads_bypassed = getattr(session, "totalAdsBypassed", 0)
            self.dialogs_dismissed = getattr(session, "totalDialogsDismissed", 0)
            self.reels_evaluated = getattr(session, "totalReelsEvaluated", 0)
            self.watchdog_recoveries = getattr(
                session, "totalWatchdogRecoveries", 0
            )

            # Check upload history from session if available
            upload_hist = getattr(session, "uploadHistory", [])
            if upload_hist:
                last_entry = upload_hist[-1]
                ts = last_entry.get("timestamp")
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts)
                        delta = datetime.now() - dt
                        secs = int(delta.total_seconds())
                        if secs < 60:
                            self.last_upload_time_str = "Just now"
                        elif secs < 3600:
                            self.last_upload_time_str = f"{secs // 60}m ago"
                        else:
                            self.last_upload_time_str = f"{secs // 3600}h {(secs % 3600) // 60}m ago"
                    except Exception:
                        pass

            u_name = getattr(session, "my_username", None)
            self.refresh_queue_status(u_name if isinstance(u_name, str) else self.username)

            args = getattr(session, "args", None)
            if args:
                self.likes_limit = _safe_int(
                    getattr(args, "current_likes_limit", None), self.likes_limit
                )
                self.follows_limit = _safe_int(
                    getattr(args, "current_follow_limit", None), self.follows_limit
                )
                self.unfollows_limit = _safe_int(
                    getattr(args, "current_unfollow_limit", None), self.unfollows_limit
                )
                self.comments_limit = _safe_int(
                    getattr(args, "current_comments_limit", None), self.comments_limit
                )
                self.watched_limit = _safe_int(
                    getattr(args, "current_watch_limit", None), self.watched_limit
                )
                self.crashes_limit = _safe_int(
                    getattr(args, "current_crashes_limit", None), self.crashes_limit
                )
                self.total_interactions_limit = _safe_int(
                    getattr(args, "current_total_limit", None),
                    self.total_interactions_limit,
                )


_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


class TuiLogHandler(logging.Handler):
    """Custom logging handler forwarding log events into the DashboardState ring buffer."""

    LEVEL_COLORS = {
        "DEBUG": "dim",
        "INFO": "bright_cyan",
        "WARNING": "bright_yellow",
        "ERROR": "bright_red",
        "CRITICAL": "bold bright_magenta",
    }

    def __init__(self, state: DashboardState):
        super().__init__()
        self.state = state

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            msg = _ANSI_ESCAPE_PATTERN.sub("", msg).strip()
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            # Handle multiline logs cleanly (tracebacks, multi-line status reports)
            lines = msg.splitlines()
            for line in lines:
                clean_line = line.strip()
                if clean_line:
                    # Truncate overly long single lines to preserve layout aesthetics
                    if len(clean_line) > 120:
                        clean_line = clean_line[:117] + "..."
                    self.state.add_log(record.levelname, timestamp, clean_line)
        except Exception:
            self.handleError(record)


class KeyboardListenerThread(threading.Thread):
    """
    Background daemon thread listening for terminal keystrokes:
    - [U] / [u]: Trigger immediate queue upload
    - [D] / [d]: Force immediate TUI re-render / debug toggle
    """

    def __init__(self, manager: "DashboardManager"):
        super().__init__(daemon=True, name="TUI-KeyboardListener")
        self.manager = manager
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        try:
            if not sys.stdin or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
                return
        except Exception:
            return

        is_win = sys.platform.startswith("win")
        if is_win:
            try:
                import msvcrt
            except ImportError:
                return

            while self._running and self.manager.is_active():
                try:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        if ch in (b"\x00", b"\xe0"):
                            msvcrt.getch()
                            continue
                        self._handle_key(ch)
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.2)
        else:
            import select

            while self._running and self.manager.is_active():
                try:
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.2)
                    if rlist:
                        key = sys.stdin.read(1)
                        self._handle_key(key)
                except Exception:
                    time.sleep(0.2)

    def _handle_key(self, key: Any):
        if key is None:
            return

        bval = key if isinstance(key, bytes) else key.encode("utf-8", errors="ignore")
        sval = key if isinstance(key, str) else key.decode("utf-8", errors="ignore")

        # CTRL+S: b'\x13' (byte 19), '\x13', or fallbacks 's', 'S', 'n', 'N'
        if bval == b"\x13" or sval in ("\x13", "s", "S", "n", "N"):
            self.manager.trigger_skip_task()
        # CTRL+U: b'\x15' (byte 21), '\x15', or fallbacks 'u', 'U'
        elif bval == b"\x15" or sval in ("\x15", "u", "U"):
            self.manager.trigger_upload_request()
        # CTRL+D: b'\x04' (byte 4), '\x04', or fallbacks 'd', 'D'
        elif bval == b"\x04" or sval in ("\x04", "d", "D"):
            self.manager.trigger_debug_toggle()


class DashboardManager:
    """Manages Rich Live layout, refresh rate, and terminal restoration."""

    _instance: Optional["DashboardManager"] = None

    def __init__(
        self,
        console: Optional[Console] = None,
        refresh_rate: float = 1.5,
        screen: bool = True,
    ):
        self.console = console or Console(force_terminal=True, safe_box=True)
        self.state = DashboardState()
        self.refresh_rate = refresh_rate
        self.screen = screen
        self.live: Optional[Live] = None
        self._active = False
        self._lock = threading.RLock()
        self._last_render_time = 0.0
        self.bound_session_state = None
        self.keyboard_thread: Optional[KeyboardListenerThread] = None
        try:
            atexit.register(self.stop)
        except Exception:
            pass

    def bind_session_state(self, session_state):
        """Bind a SessionState instance to automatically sync metrics on render."""
        with self._lock:
            self.bound_session_state = session_state
            if session_state:
                self.state.update_from_session_state(session_state)

    @classmethod
    def get_instance(cls) -> "DashboardManager":
        if cls._instance is None:
            cls._instance = DashboardManager()
        return cls._instance

    @classmethod
    def is_active(cls) -> bool:
        if cls._instance is None:
            return False
        return cls._instance._active

    def trigger_upload_request(self):
        """Handle on-demand upload hotkey [CTRL+U]."""
        with self._lock:
            self.state.upload_requested = True
            self.state.update_activity(
                action="[CTRL+U] Manual upload requested from pending queue...",
            )
            self.state.add_log(
                "INFO",
                datetime.now().strftime("%H:%M:%S"),
                "User pressed [CTRL+U]: Immediate queue photo upload requested!",
            )
            self.update_render(force=True)

    def trigger_skip_task(self):
        """Handle skip task hotkey [CTRL+S]."""
        with self._lock:
            self.state.skip_task_requested = True
            self.state.update_activity(
                action="[CTRL+S] Task skip requested! Advancing to next task...",
            )
            self.state.add_log(
                "WARNING",
                datetime.now().strftime("%H:%M:%S"),
                "User pressed [CTRL+S]: Skipping current task and advancing to next scheduled task...",
            )
            self.update_render(force=True)

    def trigger_debug_toggle(self):
        """Handle debug toggle hotkey [CTRL+D]."""
        with self._lock:
            root_logger = logging.getLogger()
            current_level = root_logger.getEffectiveLevel()
            if current_level <= logging.DEBUG:
                new_level = logging.INFO
                lvl_str = "INFO (quiet)"
            else:
                new_level = logging.DEBUG
                lvl_str = "DEBUG (verbose)"
            root_logger.setLevel(new_level)
            self.state.update_activity(
                action=f"[CTRL+D] Log level switched to {lvl_str}",
            )
            self.state.add_log(
                "INFO",
                datetime.now().strftime("%H:%M:%S"),
                f"User pressed [CTRL+D]: Log level switched to {lvl_str}. Full TUI re-render forced.",
            )
            self.update_render(force=True)

    def start(self):
        with self._lock:
            if self._active:
                return
            layout = self.generate_layout()
            self.live = Live(
                layout,
                console=self.console,
                screen=self.screen,
                refresh_per_second=self.refresh_rate,
                vertical_overflow="crop",
                transient=True if self.screen else False,
                auto_refresh=True,
            )
            self.live.start()
            self._active = True

            # Start background keyboard listener thread
            self.keyboard_thread = KeyboardListenerThread(self)
            try:
                self.keyboard_thread.start()
            except Exception:
                pass

    def stop(self):
        with self._lock:
            if not self._active:
                return
            if hasattr(self, "keyboard_thread") and self.keyboard_thread:
                try:
                    self.keyboard_thread.stop()
                except Exception:
                    pass
                self.keyboard_thread = None
            if self.live:
                try:
                    self.live.stop()
                except Exception:
                    pass
                self.live = None
            self._active = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def update_render(self, force: bool = False):
        with self._lock:
            if self.live and self._active:
                now = time.time()
                # Rate-limit manual updates to 2 Hz (0.5s interval) to prevent thread rendering collisions
                if force or (now - self._last_render_time >= 0.5):
                    self._last_render_time = now
                    try:
                        self.live.update(self.generate_layout())
                    except Exception:
                        pass

    def _render_header(self) -> Panel:
        s = self.state
        user_str = f"@{s.username}" if s.username else "No Account"
        stats_str = (
            f"({s.followers_count or '0'} followers | {s.following_count or '0'} following)"
        )
        device_str = (
            f"{s.device_id or 'Auto-Detect'} ({s.device_status})"
        )
        duration_str = s.elapsed_duration_str()

        icon_bot = safe_glyph("🤖", "[*]")
        icon_dev = safe_glyph("📱", "[Dev]")
        icon_time = safe_glyph("⏱️", "[Time]")
        sep = safe_glyph("│", "|")

        header_text = Text()
        header_text.append(f"{icon_bot} InstaAddict AI ", style="bold bright_cyan")
        header_text.append(f"v{__version__}  {sep}  ", style="dim cyan")
        header_text.append(f"{user_str} ", style="bold white")
        header_text.append(f"{stats_str}  {sep}  ", style="dim white")
        header_text.append(f"{icon_dev} Device: ", style="bold yellow")
        header_text.append(f"{device_str}  {sep}  ", style="yellow")
        header_text.append(f"{icon_time} Elapsed: ", style="bold green")
        header_text.append(f"{duration_str} (Session #{s.session_index})", style="green")

        # Watchdog Status & Blinking LED light in top-right panel corner
        led_text = Text()
        try:
            from InstaAddict.core.watchdog import BotWatchdog

            wd = BotWatchdog.get_instance()
            status = wd.get_status()
            wd_state = status.get("state", "STOPPED")
            elapsed = int(status.get("elapsed", 0))
            attempts = status.get("attempts", 0)

            blink_on = int(time.time()) % 2 == 0

            if wd_state == "HEALTHY":
                dot = safe_glyph("●", "*") if blink_on else safe_glyph("○", "o")
                style = "bold bright_green" if blink_on else "green"
                led_text.append(safe_glyph("🟢 ", "[OK] "))
                led_text.append(f"{dot} LIVE", style=style)
            elif wd_state == "PAUSED":
                dot = safe_glyph("⏸️", "||")
                led_text.append(safe_glyph("🔵 ", "[PAUSED] "))
                led_text.append(f"{dot} PAUSED", style="dim cyan")
            elif wd_state == "STALLED":
                dot = safe_glyph("●", "*")
                led_text.append(safe_glyph("🟡 ", "[!] "))
                led_text.append(
                    f"{dot} STALLED {elapsed}s", style="bold bright_yellow"
                )
            elif wd_state == "RECOVERING":
                dot = safe_glyph("▲", "^")
                fast_blink = int(time.time() * 2) % 2 == 0
                style = "bold bright_red" if fast_blink else "dim red"
                led_text.append(safe_glyph("🔴 ", "[!] "))
                led_text.append(f"{dot} RECOVERING #{attempts}", style=style)
            else:
                led_text.append(safe_glyph("⚪ ", "[-] "))
                led_text.append("IDLE", style="dim white")
        except Exception:
            dot = safe_glyph("●", "*") if int(time.time()) % 2 == 0 else safe_glyph("○", "o")
            led_text.append(safe_glyph("🟢 ", "[OK] "))
            led_text.append(f"{dot} LIVE", style="bold bright_green")

        return Panel(
            Align.center(header_text),
            title=led_text,
            title_align="right",
            style="bright_blue",
            padding=(0, 1),
        )

    def _render_stats_table(self) -> Any:
        s = self.state
        is_short = self.console.height < 28

        # 1. Main Conversion & Limits Table
        table = Table(
            expand=True,
            box=None,
            padding=(0, 0) if is_short else (0, 1),
            header_style="bold bright_cyan",
        )
        table.add_column("Metric", style="bold white", width=14)
        table.add_column("Progress", ratio=1)
        table.add_column("Count / Limit", justify="right", width=14)
        table.add_column("%", justify="right", width=6)

        metrics = [
            ("Likes", s.likes_count, s.likes_limit),
            ("Follows", s.follows_count, s.follows_limit),
            ("Unfollows", s.unfollows_count, s.unfollows_limit),
            ("Comments", s.comments_count, s.comments_limit),
            ("Watched", s.watched_count, s.watched_limit),
            ("Actions Total", s.total_interactions, s.total_interactions_limit),
            ("Crashes", s.crashes_count, s.crashes_limit),
        ]

        for name, current, limit in metrics:
            limit_val = max(limit, 1)
            pct = max(0, min(int((current / limit_val) * 100), 100))

            # Determine color threshold
            if name == "Crashes":
                bar_style = "bright_red" if current > 0 else "bright_green"
                pct_style = "bold red" if current > 0 else "dim green"
            elif pct >= 100:
                bar_style = "bright_red"
                pct_style = "bold red"
            elif pct >= 80:
                bar_style = "bright_yellow"
                pct_style = "bold yellow"
            else:
                bar_style = "bright_green"
                pct_style = "green"

            bar = ProgressBar(
                total=limit_val,
                completed=min(current, limit_val),
                width=None,
                complete_style=bar_style,
                finished_style=bar_style,
            )
            count_str = f"{current} / {limit}"
            table.add_row(
                name,
                bar,
                count_str,
                f"[{pct_style}]{pct}%[/{pct_style}]",
            )

        # 2. Pipeline Effort & Discovery (Live operational metrics)
        icon_effort = safe_glyph("⚡", "[~]")
        icon_queue = safe_glyph("📦", "[Q]")
        pass_count = max(0, s.profiles_checked - s.profiles_skipped)
        pass_pct = (pass_count / max(s.profiles_checked, 1)) * 100 if s.profiles_checked > 0 else 100.0
        pass_style = "bold green" if pass_pct >= 20 else "yellow"
        rec_color = "bold bright_red" if s.watchdog_recoveries > 0 else "bright_green"

        if is_short:
            short_rec_color = "bold red" if s.watchdog_recoveries > 0 else "dim green"
            effort_text = Text.from_markup(
                f"[bold cyan]{icon_effort} Effort:[/] Posts: [bold white]{s.posts_checked}[/] │ "
                f"Profiles: [bold white]{s.profiles_checked}[/] ([dim]{s.profiles_skipped} skp[/]) │ "
                f"Ads: [yellow]{s.ads_bypassed}[/] │ Dialogs: [green]{s.dialogs_dismissed}[/] │ "
                f"Reels: [magenta]{s.reels_evaluated}[/] │ Rec: [{short_rec_color}]{s.watchdog_recoveries}[/]"
            )
            queue_text = Text.from_markup(
                f"[bold magenta]{icon_queue} Queue:[/] [bold green]{s.queue_pending} media[/] │ "
                f"Sent: [white]{s.queue_published}[/] │ Last: [yellow]{s.last_upload_time_str}[/] │ "
                f"Slot: [cyan]{s.upload_cooldown_str}[/] │ [bold bright_magenta]\\[U] Upload Now[/]"
            )
            return Group(table, effort_text, queue_text)

        effort_header = Text.from_markup(f"\n[bold bright_cyan]{icon_effort} Real-Time Operational Effort[/] [dim](live activity counters)[/]")
        effort_table = Table(box=None, expand=True, padding=(0, 1), show_header=False)
        effort_table.add_column("C1", ratio=1)
        effort_table.add_column("C2", ratio=1)
        effort_table.add_column("C3", ratio=1)

        effort_table.add_row(
            f"[bold white]Posts Scanned:[/] [bright_cyan]{s.posts_checked}[/]",
            f"[bold white]Profiles Checked:[/] [bright_cyan]{s.profiles_checked}[/] [dim]({s.profiles_skipped} skipped)[/]",
            f"[bold white]Ads Bypassed:[/] [yellow]{s.ads_bypassed}[/]",
        )
        effort_table.add_row(
            f"[bold white]Reels Evaluated:[/] [magenta]{s.reels_evaluated}[/]",
            f"[bold white]Dialogs Cleared:[/] [green]{s.dialogs_dismissed}[/]",
            f"[bold white]Filter Pass Rate:[/] [{pass_style}]{pass_pct:.1f}%[/]",
        )
        effort_table.add_row(
            f"[bold white]Watchdog Rec:[/] [{rec_color}]{s.watchdog_recoveries}[/]",
            "[bold white]Self-Healing:[/] [bright_green]Active (3-Tier)[/]",
            "",
        )

        queue_header = Text.from_markup(f"[bold bright_magenta]{icon_queue} Content Queue & Publishing[/] [dim](hotkey: \\[U] to upload now)[/]")
        queue_table = Table(box=None, expand=True, padding=(0, 1), show_header=False)
        queue_table.add_column("Q1", ratio=1)
        queue_table.add_column("Q2", ratio=1)
        queue_table.add_column("Q3", ratio=1)

        cooldown_color = "bright_green" if s.upload_cooldown_str == "Ready" else "yellow"
        queue_table.add_row(
            f"[bold white]Pending Queue:[/] [bold green]{s.queue_pending} media[/]",
            f"[bold white]Published Total:[/] [green]{s.queue_published} posts[/]",
            f"[bold white]Last Upload:[/] [yellow]{s.last_upload_time_str}[/]",
        )
        queue_table.add_row(
            f"[bold white]Cooldown Status:[/] [{cooldown_color}]{s.upload_cooldown_str}[/]",
            f"[bold white]Uploads Session:[/] [green]{s.uploads_ok} OK[/] / [red]{s.uploads_fail} Fail[/]",
            "[bold bright_magenta]Shortcuts:[/] [bold white]\\[S] Skip  \\[U] Upload[/]",
        )

        return Group(table, effort_header, effort_table, queue_header, queue_table)

    def _render_activity_panel(self) -> Panel:
        s = self.state
        content = Text()
        bullet = safe_glyph("•", "-")

        content.append(f"{bullet} Active Job:   ", style="bold yellow")
        content.append(f"{s.current_job}\n", style="bright_white")

        content.append(f"{bullet} Current Step: ", style="bold cyan")
        content.append(f"{s.current_action}\n", style="white")

        if s.skip_task_requested:
            content.append("⚡ Task Skip Pending: Advancing to next task...\n", style="bold bright_yellow")

        if s.target_user:
            content.append(f"{bullet} Target Post:  ", style="bold magenta")
            content.append(f"@{s.target_user}", style="bright_magenta")
            if s.target_source:
                content.append(f" (source: {s.target_source})", style="dim magenta")
            content.append("\n")

        icon_cooldown = safe_glyph("⏳", "[..]")
        if s.countdown_seconds is not None and s.countdown_seconds > 0:
            content.append(f"{bullet} Cooldown:     ", style="bold bright_red")
            msg = s.countdown_message or "Next interaction in"
            content.append(f"{icon_cooldown} {msg} {s.countdown_seconds:02d}s\n", style="bold bright_yellow")
        else:
            content.append(f"{bullet} Status:       ", style="bold green")
            content.append(f"{s.status_message} (Working Hours: {s.working_hours_status})\n", style="bright_green")

        icon_act = safe_glyph("🎯", "[*]")
        return Panel(
            content,
            title=f"[bold bright_yellow]{icon_act} Active Execution Context[/bold bright_yellow]",
            border_style="yellow",
            padding=(0, 1),
        )

    def _render_logs_panel(self) -> Panel:
        s = self.state
        log_text = Text()

        with s.lock:
            entries = list(s.logs_buffer)

        # Dynamically limit visible entries based on available console height to prevent vertical overflow
        is_narrow = self.console.width < 85
        if is_narrow:
            # In 3-tier vertical stack, body is shared between stats, activity, logs
            max_visible = max(3, int(self.console.height * 0.3) - 2)
        else:
            # In dual-column, logs panel occupies the entire right column height minus header and footer
            max_visible = max(3, self.console.height - 8)

        visible_entries = (
            entries[-max_visible:] if len(entries) > max_visible else entries
        )

        if not visible_entries:
            log_text.append("Waiting for runtime logs...", style="dim")
        else:
            for level, timestamp, message in visible_entries:
                color = TuiLogHandler.LEVEL_COLORS.get(level, "white")
                log_text.append(f"[{timestamp}] ", style="dim")
                log_text.append(f"[{level[:4]:<4}] ", style=color)
                log_text.append(f"{message}\n", style="white")

        icon_log = safe_glyph("📜", "[=]")
        return Panel(
            log_text,
            title=f"[bold bright_cyan]{icon_log} Live Rolling Console[/bold bright_cyan]",
            border_style="cyan",
            padding=(0, 1),
        )

    def _render_footer(self) -> Panel:
        sep = safe_glyph("│", "|")
        footer_text = Text()
        footer_text.append(" [Ctrl+C] ", style="bold bright_red")
        footer_text.append(f"Stop  {sep} ", style="dim white")
        footer_text.append(" [Ctrl+S] ", style="bold bright_yellow")
        footer_text.append(f"Skip Task  {sep} ", style="bright_white")
        footer_text.append(" [Ctrl+U] ", style="bold bright_magenta")
        footer_text.append(f"Upload Queued Photo  {sep} ", style="bright_white")
        footer_text.append(" [Ctrl+D] ", style="bold bright_yellow")
        footer_text.append(f"Debug  {sep} ", style="dim white")
        footer_text.append(" Mode: ", style="bold cyan")
        footer_text.append(f"Live (Human Sim)  {sep} ", style="bold green")
        footer_text.append(" Queue: ", style="bold green")
        cooldown_style = "bright_green" if self.state.upload_cooldown_str == "Ready" else "yellow"
        footer_text.append(
            f"{self.state.queue_pending} pending ({self.state.upload_cooldown_str})",
            style=cooldown_style,
        )

        return Panel(
            Align.center(footer_text),
            style="dim white",
            padding=(0, 1),
        )

    def generate_layout(self) -> Layout:
        """Construct the full terminal layout with responsive width adaptation."""
        if self.bound_session_state:
            self.state.update_from_session_state(self.bound_session_state)

        layout = Layout()

        # Top-level vertical split: Header, Body, Footer
        layout.split_column(
            Layout(self._render_header(), name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(self._render_footer(), name="footer", size=3),
        )

        icon_stats = safe_glyph("📊", "[#]")
        stats_panel = Panel(
            self._render_stats_table(),
            title=f"[bold bright_green]{icon_stats} Session Statistics, Effort & Queue[/bold bright_green]",
            border_style="green",
            padding=(0, 1),
        )
        activity_panel = self._render_activity_panel()
        logs_panel = self._render_logs_panel()

        # Responsive layout: If terminal is narrow (< 85 cols), stack vertically
        if self.console.width < 85:
            layout["body"].split_column(
                Layout(stats_panel, name="stats", ratio=4),
                Layout(activity_panel, name="activity", ratio=2),
                Layout(logs_panel, name="logs", ratio=4),
            )
        else:
            left_column = Layout(name="left", ratio=1)
            left_column.split_column(
                Layout(stats_panel, name="stats", ratio=5),
                Layout(activity_panel, name="activity", ratio=3),
            )
            right_column = Layout(logs_panel, name="logs", ratio=1)
            layout["body"].split_row(left_column, right_column)

        return layout

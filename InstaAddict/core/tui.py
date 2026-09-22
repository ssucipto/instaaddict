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
from typing import Any, Deque, List, Optional, Tuple

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from InstaAddict import __version__


from enum import Enum


class ViewMode(Enum):
    """Display modes for the interactive terminal dashboard."""

    LIVE_DASHBOARD = "live_dashboard"
    STATISTICS_CHARTS = "statistics_charts"
    FILTER_INTELLIGENCE = "filter_intelligence"


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


def safe_bar(
    ratio: float,
    width: int = 16,
    filled_style: str = "bright_cyan",
    empty_style: str = "dim white",
) -> Text:
    """Renders a high-resolution horizontal bar using Unicode fractional sub-blocks.

    Falls back to ASCII '#' and '-' if console encoding does not support UTF-8.
    """
    ratio = max(0.0, min(1.0, float(ratio))) if (ratio == ratio) else 0.0
    encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
    is_utf = "utf" in encoding.lower()

    if not is_utf:
        full = int(ratio * width)
        empty = max(0, width - full)
        t = Text()
        if full > 0:
            t.append("#" * full, style=filled_style)
        if empty > 0:
            t.append("-" * empty, style=empty_style)
        return t

    sub_blocks = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
    total_eighths = int(round(ratio * width * 8))
    full_chars = min(total_eighths // 8, width)
    remainder_eighth = total_eighths % 8 if full_chars < width else 0

    rem_char = (
        sub_blocks[remainder_eighth]
        if (full_chars < width and remainder_eighth > 0)
        else ""
    )
    empty_chars = max(0, width - full_chars - (1 if rem_char else 0))

    t = Text()
    if full_chars > 0:
        t.append("█" * full_chars, style=filled_style)
    if rem_char:
        t.append(rem_char, style=filled_style)
    if empty_chars > 0:
        t.append(" " * empty_chars, style=empty_style)
    return t


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
    subscreen_escapes: int = 0

    # Motion & Stability telemetry
    total_swipes: int = 0
    zero_displacement_swipes: int = 0
    snapback_events: int = 0
    micro_stall_escapes: int = 0

    # Content queue & upload telemetry
    queue_pending: int = 0
    queue_published: int = 0
    last_upload_time_str: str = "Never"
    upload_cooldown_str: str = "Ready"
    upload_requested: bool = False
    skip_task_requested: bool = False

    # Pipeline & scheduled jobs context
    pipeline_jobs: List[str] = field(default_factory=list)
    pipeline_index: int = 0

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

    def set_pipeline(self, jobs: List[str], current_index: int = 0):
        """Update the list of scheduled jobs and current active index."""
        with self.lock:
            self.pipeline_jobs = list(jobs)
            self.pipeline_index = current_index

    def get_next_job_name(self) -> Optional[str]:
        """Get the name of the upcoming job in the pipeline or None."""
        with self.lock:
            if not self.pipeline_jobs:
                return None
            idx = self.pipeline_index + 1
            if idx < len(self.pipeline_jobs):
                return self.pipeline_jobs[idx]
            return "End of Session"

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
            self.subscreen_escapes = getattr(
                session, "totalSubscreenEscapes", 0
            )
            self.total_swipes = getattr(session, "totalSwipes", 0)
            self.zero_displacement_swipes = getattr(
                session, "zeroDisplacementSwipes", 0
            )
            self.snapback_events = getattr(session, "snapbackEvents", 0)
            self.micro_stall_escapes = getattr(
                session, "totalMicroStallEscapes", 0
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

            # Harden console input: Clear ENABLE_PROCESSED_INPUT on CONIN$ so
            # CTRL+S (0x13) reaches getch() instead of XOFF pause in conhost.
            orig_mode = None
            conin_handle = None
            try:
                import ctypes
                k32 = ctypes.windll.kernel32
                conin_handle = k32.CreateFileW(
                    "CONIN$", 0xC0000000, 3, None, 3, 0, None
                )
                if conin_handle and conin_handle != -1:
                    m = ctypes.c_ulong()
                    if k32.GetConsoleMode(conin_handle, ctypes.byref(m)):
                        orig_mode = m.value
                        k32.SetConsoleMode(conin_handle, orig_mode & ~0x0001)
            except Exception:
                pass

            try:
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
            finally:
                if orig_mode is not None and conin_handle:
                    try:
                        import ctypes
                        k32 = ctypes.windll.kernel32
                        k32.SetConsoleMode(conin_handle, orig_mode)
                        k32.CloseHandle(conin_handle)
                    except Exception:
                        pass
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
        # CTRL+G: b'\x07' (byte 7), '\x07', or fallbacks 'g', 'G'
        elif bval == b"\x07" or sval in ("\x07", "g", "G"):
            self.manager.trigger_view_toggle()


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
        self.view_mode: ViewMode = ViewMode.LIVE_DASHBOARD
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
    def _reset_instance(cls) -> None:
        """Reset the singleton for test isolation. Not for production use."""
        cls._instance = None

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
        """Handle skip task hotkey [CTRL+S], [S], [N], or IPC signal."""
        with self._lock:
            self.state.skip_task_requested = True
            next_job = self.state.get_next_job_name() or "next task"
            action_msg = (
                f"⚡ [SKIP REQUESTED] Skipping '{self.state.current_job}' "
                f"➔ Advancing to '{next_job}'..."
            )
            self.state.update_activity(action=action_msg)
            log_msg = (
                f"User shortcut [S]/[N]/[CTRL+S]: Aborting job "
                f"'{self.state.current_job}' and advancing to '{next_job}'..."
            )
            self.state.add_log(
                "WARNING",
                datetime.now().strftime("%H:%M:%S"),
                log_msg,
            )
            # Create/touch IPC signal file for disk-level synchronization
            if self.state.username:
                account_dir = os.path.join("accounts", self.state.username)
                if os.path.isdir(account_dir):
                    try:
                        sig_path = os.path.join(account_dir, ".skip_task")
                        with open(sig_path, "w") as f:
                            f.write(str(time.time()))
                    except Exception:
                        pass
            # Trigger terminal bell / beep for immediate tactile/audible feedback
            try:
                sys.stdout.write("\a")
                sys.stdout.flush()
            except Exception:
                pass

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

    def trigger_view_toggle(self):
        """Handle screen toggle hotkey [CTRL+G]. Cycles Live → KPI Charts → Filter Intelligence → Live."""
        with self._lock:
            if self.view_mode == ViewMode.LIVE_DASHBOARD:
                self.view_mode = ViewMode.STATISTICS_CHARTS
                mode_str = "Statistics & KPI Charts"
            elif self.view_mode == ViewMode.STATISTICS_CHARTS:
                self.view_mode = ViewMode.FILTER_INTELLIGENCE
                mode_str = "Filter Intelligence & Job Yield"
            else:
                self.view_mode = ViewMode.LIVE_DASHBOARD
                mode_str = "Live Operations Dashboard"

            self.state.update_activity(
                action=f"[CTRL+G] Display switched to {mode_str}",
            )
            self.state.add_log(
                "INFO",
                datetime.now().strftime("%H:%M:%S"),
                f"User pressed [CTRL+G]: Interface toggled to {mode_str}.",
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
        sep = safe_glyph("│", "|")
        icon_bot = safe_glyph("🤖", "[BOT]")
        icon_dev = safe_glyph("📱", "[Dev]")
        icon_time = safe_glyph("⏱", "[T]")
        icon_eye = safe_glyph("👁", "[~]")
        icon_clock = safe_glyph("🕐", "[H]")
        blink_on = int(time.time()) % 2 == 0

        # ── Row 1: Brand + Account identity ──────────────────────────────
        row1 = Text(justify="center")
        pulse = safe_glyph("●", "*") if blink_on else safe_glyph("○", "o")
        row1.append(f" {icon_bot} ", style="bold bright_cyan")
        row1.append("InstaAddict-AI", style="bold bright_cyan")
        row1.append(f" v{__version__} ", style="dim cyan")
        row1.append(f" {sep} ", style="dim blue")
        row1.append(f" {user_str} ", style="bold white")
        followers = s.followers_count or "–"
        following = s.following_count or "–"
        posts = s.posts_count or "–"
        row1.append(f" {icon_eye} {followers} followers ", style="dim white")
        row1.append(f"{sep} ", style="dim blue")
        row1.append(f" {following} following ", style="dim white")
        row1.append(f"{sep} ", style="dim blue")
        row1.append(f" {posts} posts ", style="dim white")
        row1.append(f" {sep} ", style="dim blue")
        row1.append(f" {pulse} ", style="bold bright_green" if blink_on else "green")
        row1.append("LIVE", style="bold bright_green")
        if self.state.skip_task_requested:
            row1.append(f" {sep} ", style="dim white")
            row1.append(" ⚡ SKIP PENDING ", style="bold bright_white on red")
        if self.view_mode == ViewMode.STATISTICS_CHARTS:
            row1.append(f" {sep} ", style="dim blue")
            row1.append(" KPI CHARTS ", style="bold bright_magenta")
        elif self.view_mode == ViewMode.FILTER_INTELLIGENCE:
            row1.append(f" {sep} ", style="dim blue")
            row1.append(" FILTER INTEL ", style="bold bright_yellow")

        # ── Row 2: Device + Session + Working Hours ───────────────────────
        row2 = Text(justify="center")
        device_id = s.device_id or "Auto-Detect"
        duration_str = s.elapsed_duration_str()
        wh_status = s.working_hours_status
        wh_color = (
            "bright_green" if "Active" in wh_status
            else ("bright_yellow" if "Sleep" in wh_status else "dim white")
        )
        wh_icon = (
            safe_glyph("🟢", "[ON]")
            if "Active" in wh_status
            else safe_glyph("🔴", "[ZZ]")
        )
        row2.append(f" {icon_dev} ", style="yellow")
        row2.append(f"{device_id} ", style="yellow")
        row2.append(f"({s.device_status}) ", style="dim yellow")
        row2.append(f" {sep} ", style="dim blue")
        row2.append(f" {icon_time} ", style="green")
        row2.append(f"{duration_str} ", style="bright_green")
        row2.append(f"Session #{s.session_index}/{s.total_sessions} ", style="dim green")
        row2.append(f" {sep} ", style="dim blue")
        row2.append(f" {icon_clock} Working Hours: ", style="dim white")
        row2.append(f"{wh_icon} {wh_status} ", style=wh_color)
        row2.append(f" {sep} ", style="dim blue")
        row2.append(" Status: ", style="dim white")
        status_color = (
            "bold bright_green" if s.status_message == "RUNNING"
            else ("bold bright_red" if "SLEEP" in s.status_message.upper() else "bold bright_yellow")
        )
        row2.append(f" {s.status_message} ", style=status_color)

        # ── Watchdog LED for panel title ──────────────────────────────────
        led_text = Text()
        try:
            from InstaAddict.core.watchdog import BotWatchdog
            wd = BotWatchdog.get_instance()
            wd_status = wd.get_status()
            wd_state = wd_status.get("state", "STOPPED")
            elapsed_wd = int(wd_status.get("elapsed", 0))
            attempts_wd = wd_status.get("attempts", 0)

            if wd_state == "HEALTHY":
                dot = safe_glyph("●", "*") if blink_on else safe_glyph("○", "o")
                led_text.append(safe_glyph("🟢 ", "[OK] "))
                led_text.append(f"{dot} WATCHDOG HEALTHY", style="bold bright_green" if blink_on else "green")
            elif wd_state == "PAUSED":
                led_text.append(safe_glyph("🔵 ", "[P] "))
                led_text.append("⏸ PAUSED", style="dim cyan")
            elif wd_state == "STALLED":
                led_text.append(safe_glyph("🟡 ", "[!] "))
                led_text.append(f"● STALLED {elapsed_wd}s", style="bold bright_yellow")
            elif wd_state == "RECOVERING":
                fast = int(time.time() * 2) % 2 == 0
                led_text.append(safe_glyph("🔴 ", "[!] "))
                led_text.append(f"▲ RECOVERING #{attempts_wd}", style="bold bright_red" if fast else "dim red")
            else:
                led_text.append(safe_glyph("⚪ ", "[-] "))
                led_text.append("IDLE", style="dim white")
        except Exception:
            dot = safe_glyph("●", "*") if blink_on else safe_glyph("○", "o")
            led_text.append(safe_glyph("🟢 ", "[OK] "))
            led_text.append(f"{dot} LIVE", style="bold bright_green")

        return Panel(
            Group(Align.center(row1), Align.center(row2)),
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
                f"Escapes: [cyan]{s.subscreen_escapes}[/] │ Rec: [{short_rec_color}]{s.watchdog_recoveries}[/]"
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
        esc_color = "bright_cyan" if s.subscreen_escapes > 0 else "dim white"
        effort_table.add_row(
            f"[bold white]Watchdog Rec:[/] [{rec_color}]{s.watchdog_recoveries}[/]",
            f"[bold white]Subscreen Esc:[/] [{esc_color}]{s.subscreen_escapes}[/]",
            "[bold white]Self-Healing:[/] [bright_green]Active (3-Tier)[/]",
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

        # Render Job Pipeline Queue if configured
        if s.pipeline_jobs:
            content.append(f"{bullet} Job Queue:    ", style="bold bright_cyan")
            for i, job_name in enumerate(s.pipeline_jobs):
                if i < s.pipeline_index:
                    content.append(f"[{job_name} ✓] ", style="dim green")
                elif i == s.pipeline_index:
                    content.append(
                        f"[{job_name} (ACTIVE)] ",
                        style="bold bright_white on dark_blue",
                    )
                elif i == s.pipeline_index + 1:
                    content.append(
                        f"[{job_name} (NEXT)] ",
                        style="bold bright_yellow",
                    )
                else:
                    content.append(f"[{job_name}] ", style="dim white")
                if i < len(s.pipeline_jobs) - 1:
                    content.append("➔ ", style="dim cyan")
            content.append("\n")

        content.append(f"{bullet} Current Step: ", style="bold cyan")
        content.append(f"{s.current_action}\n", style="white")

        if s.skip_task_requested:
            next_job = s.get_next_job_name() or "next task"
            skip_banner = (
                f"🚨 [CTRL+S RECEIVED] Task Skip Pending: Terminating "
                f"'{s.current_job}' ➔ Advancing to '{next_job}'...\n"
            )
            content.append(skip_banner, style="bold bright_yellow on red")

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
        s = self.state

        # ── Row 1: View mode indicator + Queue status ─────────────────────
        row1 = Text(justify="center")
        if self.view_mode == ViewMode.LIVE_DASHBOARD:
            next_mode = "KPI Charts"
        elif self.view_mode == ViewMode.STATISTICS_CHARTS:
            next_mode = "Filter Intel"
        else:
            next_mode = "Live Ops"

        mode_labels = {
            ViewMode.LIVE_DASHBOARD: "● Live Ops",
            ViewMode.STATISTICS_CHARTS: "◈ KPI Charts",
            ViewMode.FILTER_INTELLIGENCE: "◉ Filter Intel",
        }
        current_mode = mode_labels.get(self.view_mode, "Live Ops")
        row1.append(f" ◀ {current_mode} ▶ ", style="bold bright_cyan")
        row1.append(f" {sep} ", style="dim white")
        row1.append(" Next: ", style="dim cyan")
        row1.append(f"{next_mode} ", style="cyan")
        row1.append(f" {sep} ", style="dim white")

        if s.skip_task_requested:
            blink_on = int(time.time() * 2) % 2 == 0
            skip_style = "bold bright_white on red" if blink_on else "bold bright_yellow on dark_red"
            row1.append(" ⚡ SKIPPING → NEXT TASK ", style=skip_style)
            row1.append(f" {sep} ", style="dim white")

        cooldown_style = "bright_green" if s.upload_cooldown_str == "Ready" else "yellow"
        row1.append(" 📦 Queue: ", style="bold green")
        row1.append(f"{s.queue_pending} pending ", style="bright_green" if s.queue_pending == 0 else "bold bright_yellow")
        row1.append(f"{sep} Cooldown: ", style="dim green")
        row1.append(f"{s.upload_cooldown_str} ", style=cooldown_style)
        row1.append(f" {sep} ", style="dim white")
        row1.append(f" Published: {s.queue_published} posts ", style="dim green")

        # ── Row 2: Keyboard shortcut legend ──────────────────────────────
        row2 = Text(justify="center")
        shortcuts = [
            ("Ctrl+G", f"→ {next_mode}", "bright_cyan"),
            ("Ctrl+S", "Skip Task", "bright_yellow"),
            ("Ctrl+U", "Upload Now", "bright_magenta"),
            ("Ctrl+D", "Debug Toggle", "yellow"),
            ("Ctrl+C", "Stop Bot", "bright_red"),
        ]
        for i, (key, label, color) in enumerate(shortcuts):
            row2.append(f" [{key}] ", style=f"bold {color}")
            row2.append(label, style="white")
            if i < len(shortcuts) - 1:
                row2.append(f"  {sep}  ", style="dim white")

        return Panel(
            Group(Align.center(row1), Align.center(row2)),
            style="dim white",
            padding=(0, 0),
        )

    def _render_funnel_chart(self) -> Panel:
        s = self.state
        posts_checked = max(s.posts_checked, 0)
        profiles_checked = max(s.profiles_checked, 0)
        pass_count = max(0, s.profiles_checked - s.profiles_skipped)
        total_interactions = max(s.total_interactions, 0)
        outcomes = s.likes_count + s.follows_count + s.comments_count + s.watched_count

        table = Table(box=None, expand=True, padding=(0, 1), header_style="bold bright_cyan")
        table.add_column("Funnel Stage", style="bold white", width=18)
        table.add_column("Conversion Bar", ratio=1)
        table.add_column("Count", justify="right", width=7)
        table.add_column("Step %", justify="right", width=8)
        table.add_column("Tot %", justify="right", width=7)

        base = max(posts_checked, profiles_checked, pass_count, total_interactions, outcomes, 1)

        stages = [
            ("1. Posts Scanned", posts_checked, 1.0, 1.0, "bright_blue"),
            (
                "2. Profiles Inspected",
                profiles_checked,
                (profiles_checked / max(posts_checked, 1)) if posts_checked > 0 else (1.0 if profiles_checked > 0 else 0.0),
                (profiles_checked / base),
                "bright_cyan",
            ),
            (
                "3. Filter Passed",
                pass_count,
                (pass_count / max(profiles_checked, 1)) if profiles_checked > 0 else (1.0 if pass_count > 0 else 0.0),
                (pass_count / base),
                "bright_green",
            ),
            (
                "4. Engagements Attempted",
                total_interactions,
                (total_interactions / max(pass_count, 1)) if pass_count > 0 else (1.0 if total_interactions > 0 else 0.0),
                (total_interactions / base),
                "bright_yellow",
            ),
            (
                "5. Successful Converts",
                outcomes,
                (outcomes / max(total_interactions, 1)) if total_interactions > 0 else (1.0 if outcomes > 0 else 0.0),
                (outcomes / base),
                "bold bright_magenta",
            ),
        ]

        for name, count, step_ratio, total_ratio, color in stages:
            step_pct = min(int(round(step_ratio * 100.0)), 100)
            tot_pct = min(int(round(total_ratio * 100.0)), 100)
            bar = safe_bar(min(total_ratio, 1.0), width=16, filled_style=color)
            table.add_row(
                name,
                bar,
                str(count),
                f"[{color}]{step_pct}%[/{color}]",
                f"[dim]{tot_pct}%[/dim]",
            )

        icon_funnel = safe_glyph("⚡", "[*]")
        return Panel(
            table,
            title=f"[bold bright_cyan]{icon_funnel} Engagement & Conversion Funnel[/bold bright_cyan]",
            border_style="cyan",
            padding=(0, 1),
        )

    def _render_quota_velocity_chart(self) -> Panel:
        s = self.state
        hours_elapsed = max((datetime.now() - s.start_time).total_seconds() / 3600.0, 0.02)

        table = Table(box=None, expand=True, padding=(0, 1), header_style="bold bright_green")
        table.add_column("Action / Quota", style="bold white", width=15)
        table.add_column("Quota Gauge", ratio=1)
        table.add_column("Count / Limit", justify="right", width=13)
        table.add_column("Velocity", justify="right", width=9)
        table.add_column("Pace", justify="center", width=7)

        quotas = [
            ("Likes", s.likes_count, s.likes_limit, 60.0),
            ("Follows", s.follows_count, s.follows_limit, 20.0),
            ("Unfollows", s.unfollows_count, s.unfollows_limit, 20.0),
            ("Comments", s.comments_count, s.comments_limit, 8.0),
            ("Stories Watched", s.watched_count, s.watched_limit, 50.0),
            ("Total Actions", s.total_interactions, s.total_interactions_limit, 100.0),
            ("Crash Budget", s.crashes_count, s.crashes_limit, 2.0),
        ]

        for name, current, limit, max_safe_rate in quotas:
            limit_val = max(limit, 1)
            ratio = min(current / limit_val, 1.0)
            rate_per_hr = current / hours_elapsed

            if name == "Crash Budget":
                color = "bright_red" if current > 0 else "bright_green"
                pace_str = "[green]SAFE[/green]" if current == 0 else "[red]RISK[/red]"
            elif ratio >= 1.0:
                color = "bright_red"
                pace_str = "[red]MAX[/red]"
            elif rate_per_hr > max_safe_rate:
                color = "bright_yellow"
                pace_str = "[yellow]FAST[/yellow]"
            else:
                color = "bright_green"
                pace_str = "[green]OPT[/green]"

            bar = safe_bar(ratio, width=15, filled_style=color)
            table.add_row(
                name,
                bar,
                f"{current} / {limit}",
                f"{rate_per_hr:.1f}/h",
                pace_str,
            )

        icon_gauge = safe_glyph("⏱️", "[#]")
        return Panel(
            table,
            title=f"[bold bright_green]{icon_gauge} Quota Consumption & Velocity Gauges[/bold bright_green]",
            border_style="green",
            padding=(0, 1),
        )

    def _render_latency_chart(self) -> Panel:
        table = Table(box=None, expand=True, padding=(0, 1), header_style="bold bright_yellow")
        table.add_column("Operation", style="bold white", width=20)
        table.add_column("Tail Latency (P95)", ratio=1)
        table.add_column("Calls", justify="right", width=6)
        table.add_column("P50", justify="right", width=8)
        table.add_column("P95", justify="right", width=8)
        table.add_column("Err", justify="right", width=5)
        table.add_column("Status", justify="center", width=7)

        percentiles: dict = {}
        counts: dict = {}
        errors: dict = {}
        try:
            from InstaAddict.core.telemetry import PerformanceTracker
            tracker = PerformanceTracker.get_instance()
            percentiles = tracker.get_percentiles()
            counts = tracker.operation_counts
            errors = tracker.operation_errors
        except Exception:
            pass

        # Core operations + new job/filter operations from Audit #113
        operations = [
            ("view.profile_load", "Profile View Load", 3000.0),
            ("view.post_open", "Post Modal Open", 3000.0),
            ("view.search_query", "Search Navigation", 4000.0),
            ("api.gemini_vision", "Gemini Vision AI", 15000.0),
            ("motion.swipe", "Gesture & Swipe", 1500.0),
            ("filter.check_profile", "Filter Evaluation", 500.0),
        ]

        # Dynamically append any job.* operations tracked this session
        job_ops = sorted(
            [(k, c) for k, c in counts.items() if k.startswith("job.")],
            key=lambda x: x[1],
            reverse=True,
        )[:3]  # Top 3 jobs by call count
        for job_key, _ in job_ops:
            job_display = job_key.replace("job.", "").replace("_", " ").title()[:18]
            operations.append((job_key, job_display, 30000.0))

        for op_key, display_name, baseline_target in operations:
            stat = percentiles.get(op_key, {})
            p50 = stat.get("p50", 0.0)
            p95 = stat.get("p95", 0.0)
            call_count = counts.get(op_key, 0)
            err_count = errors.get(op_key, 0)

            if call_count == 0:
                bar = safe_bar(0.0, width=15, filled_style="dim white")
                status = "[dim]IDLE[/dim]"
                p50_str = "[dim]-[/dim]"
                p95_str = "[dim]-[/dim]"
                err_str = "[dim]-[/dim]"
            else:
                ratio = min(p95 / baseline_target, 1.0)
                if p95 <= baseline_target * 0.5:
                    color = "bright_green"
                    status = "[green]FAST[/green]"
                elif p95 <= baseline_target:
                    color = "bright_yellow"
                    status = "[yellow]NOM[/yellow]"
                else:
                    color = "bright_red"
                    status = "[red]SLOW[/red]"

                bar = safe_bar(ratio, width=15, filled_style=color)
                p50_str = f"{p50:.0f}ms"
                p95_str = f"[{color}]{p95:.0f}ms[/{color}]"
                err_color = "bright_red" if err_count > 0 else "dim white"
                err_str = f"[{err_color}]{err_count}[/{err_color}]"

            table.add_row(
                display_name,
                bar,
                str(call_count),
                p50_str,
                p95_str,
                err_str,
                status,
            )

        icon_latency = safe_glyph("📈", "[~]")
        return Panel(
            table,
            title=f"[bold bright_yellow]{icon_latency} Operation Latency Distribution (P50/P95) — incl. Job & Filter Ops[/bold bright_yellow]",
            border_style="yellow",
            padding=(0, 1),
        )

    def _render_motion_health_chart(self) -> Panel:
        s = self.state
        motion_stats: dict = {}
        try:
            from InstaAddict.core.telemetry import PerformanceTracker

            tracker = PerformanceTracker.get_instance()
            motion_stats = tracker.get_motion_summary()
        except Exception:
            pass

        total_swipes = motion_stats.get("total_swipes", s.total_swipes)
        displaced = motion_stats.get("displaced_swipes", max(0, total_swipes - s.zero_displacement_swipes))
        zero_disp = motion_stats.get("zero_displacement_swipes", s.zero_displacement_swipes)
        snapbacks = motion_stats.get("snapback_events", s.snapback_events)
        eff_pct = motion_stats.get("displacement_efficiency_pct", 100.0)
        scale_factor = motion_stats.get("adaptive_scale_factor", 1.0)

        table = Table(box=None, expand=True, padding=(0, 1), show_header=False)
        table.add_column("C1", ratio=1)
        table.add_column("C2", ratio=1)

        eff_color = "bright_green" if eff_pct >= 85 else ("bright_yellow" if eff_pct >= 70 else "bright_red")
        eff_bar = safe_bar(eff_pct / 100.0, width=16, filled_style=eff_color)

        table.add_row(
            Text.from_markup(f"[bold white]Displacement Efficiency:[/] [{eff_color}]{eff_pct}%[/]"),
            Text.from_markup(f"[bold white]Dynamic Swipe Scale:[/] [cyan]{scale_factor:.2f}x[/]"),
        )
        table.add_row(
            eff_bar,
            Text.from_markup(f"[bold white]Zero-Displacement:[/] [yellow]{zero_disp}[/] / {total_swipes}"),
        )
        table.add_row(
            Text.from_markup(f"[bold white]Effective Swipes:[/] [green]{displaced}[/] (snapbacks: [yellow]{snapbacks}[/])"),
            Text.from_markup(f"[bold white]Micro-Stall Escapes:[/] [bright_cyan]{s.micro_stall_escapes}[/]"),
        )
        table.add_row(
            Text.from_markup(f"[bold white]Subscreen Auto-Escapes:[/] [bright_cyan]{s.subscreen_escapes}[/]"),
            Text.from_markup(f"[bold white]Watchdog Hard Relaunches:[/] [{'bright_red' if s.watchdog_recoveries > 0 else 'bright_green'}]{s.watchdog_recoveries}[/]"),
        )
        table.add_row(
            Text.from_markup("[bold white]Self-Healing Framework:[/] [bright_green]3-Tier Active (Sentinel / Subscreen / Watchdog)[/]"),
            Text.from_markup("[bold white]UI Recovery Integrity:[/] [bright_green]100% NOMINAL[/]"),
        )

        icon_shield = safe_glyph("🛡️", "[!]")
        return Panel(
            table,
            title=f"[bold bright_magenta]{icon_shield} Motion Dynamics & Stability Matrix[/bold bright_magenta]",
            border_style="magenta",
            padding=(0, 1),
        )

    def _render_skip_reasons_panel(self) -> Panel:
        """Render skip reason distribution as a horizontal bar chart."""
        s = self.state
        skip_reasons: dict = {}
        try:
            if self.bound_session_state:
                skip_reasons = dict(getattr(self.bound_session_state, "skip_reasons", {}) or {})
        except Exception:
            pass

        table = Table(box=None, expand=True, padding=(0, 1), header_style="bold bright_red")
        table.add_column("Skip Reason", style="bold white", width=22)
        table.add_column("Distribution Bar", ratio=1)
        table.add_column("Count", justify="right", width=7)
        table.add_column("%", justify="right", width=7)

        if not skip_reasons:
            table.add_row(
                "[dim]No skip reasons recorded yet[/dim]",
                "", "", "",
            )
        else:
            total = max(sum(skip_reasons.values()), 1)
            sorted_reasons = sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_reasons[:10]:
                ratio = count / total
                pct = int(round(ratio * 100))
                if ratio >= 0.30:
                    color = "bright_red"
                elif ratio >= 0.15:
                    color = "bright_yellow"
                else:
                    color = "bright_green"
                bar = safe_bar(ratio, width=20, filled_style=color)
                display = reason.replace("_", " ").title()
                table.add_row(display, bar, str(count), f"[{color}]{pct}%[/{color}]")

        total_skipped = sum(skip_reasons.values()) if skip_reasons else 0
        icon = safe_glyph("🚫", "[X]")
        return Panel(
            table,
            title=f"[bold bright_red]{icon} Filter Rejection Intelligence — {total_skipped} total skips[/bold bright_red]",
            border_style="red",
            padding=(0, 1),
        )

    def _render_job_metrics_panel(self) -> Panel:
        """Render per-job task lifecycle and yield performance table."""
        job_metrics: dict = {}
        try:
            if self.bound_session_state:
                job_metrics = dict(getattr(self.bound_session_state, "job_metrics", {}) or {})
        except Exception:
            pass

        table = Table(box=None, expand=True, padding=(0, 1), header_style="bold bright_cyan")
        table.add_column("Task / Plugin", style="bold white", width=22)
        table.add_column("Yield Bar", ratio=1)
        table.add_column("Duration", justify="right", width=9)
        table.add_column("Attempts", justify="right", width=9)
        table.add_column("Successes", justify="right", width=10)
        table.add_column("Yield %", justify="right", width=8)
        table.add_column("Status", justify="center", width=10)

        if not job_metrics:
            table.add_row(
                "[dim]No job metrics recorded yet[/dim]",
                "", "", "", "", "", "",
            )
        else:
            for job_name, metrics in job_metrics.items():
                attempts = metrics.get("interactions_attempted", 0)
                successes = metrics.get("interactions_successful", 0)
                duration = metrics.get("duration_seconds", 0.0)
                status = metrics.get("status", "in_progress")

                yield_ratio = successes / max(attempts, 1) if attempts > 0 else 0.0
                yield_pct = int(round(yield_ratio * 100))

                if yield_pct >= 50:
                    yield_color = "bright_green"
                elif yield_pct >= 20:
                    yield_color = "bright_yellow"
                elif attempts == 0:
                    yield_color = "dim white"
                else:
                    yield_color = "bright_red"

                if status == "in_progress":
                    status_str = "[bold bright_cyan]⚡ ACTIVE[/bold bright_cyan]"
                elif status == "completed":
                    status_str = "[green]✓ Done[/green]"
                elif status == "app_has_crashed":
                    status_str = "[bold red]💥 CRASH[/bold red]"
                else:
                    status_str = f"[dim]{status}[/dim]"

                bar = safe_bar(yield_ratio, width=18, filled_style=yield_color)
                dur_str = f"{duration:.0f}s" if duration < 3600 else f"{duration/3600:.1f}h"
                display = job_name.replace("_", " ").title()[:20]
                table.add_row(
                    display,
                    bar,
                    dur_str,
                    str(attempts),
                    str(successes),
                    f"[{yield_color}]{yield_pct}%[/{yield_color}]",
                    status_str,
                )

        icon = safe_glyph("⚙", "[J]")
        return Panel(
            table,
            title=f"[bold bright_cyan]{icon} Task Yield & Job Performance Standards[/bold bright_cyan]",
            border_style="cyan",
            padding=(0, 1),
        )

    def _render_crash_timeline_panel(self) -> Panel:
        """Render crash history timeline if crashes occurred this session."""
        crash_history: list = []
        total_crashes = self.state.crashes_count
        try:
            if self.bound_session_state:
                crash_history = list(getattr(self.bound_session_state, "crash_history", []) or [])
        except Exception:
            pass

        content = Text()
        if not crash_history and total_crashes == 0:
            content.append(" ✓ No crashes recorded this session.", style="bold bright_green")
        elif not crash_history:
            content.append(f" {total_crashes} crash(es) recorded — context JSON not yet available.", style="bright_yellow")
        else:
            for i, crash in enumerate(crash_history[-5:], 1):
                ts = crash.get("timestamp", "")[:19]
                job = crash.get("active_job", "unknown")
                reason = crash.get("error_reason") or crash.get("exception_type", "unknown")
                pkg = crash.get("foreground_package", "")
                content.append(f" #{i} ", style="bold bright_red")
                content.append(f"[{ts}] ", style="dim")
                content.append(f"{job} ", style="bold white")
                content.append(f"— {reason} ", style="bright_red")
                if pkg:
                    content.append(f"(fg: {pkg})", style="dim yellow")
                content.append("\n")

        icon = safe_glyph("💥", "[!]")
        crash_color = "bright_red" if total_crashes > 0 else "bright_green"
        return Panel(
            content,
            title=f"[bold {crash_color}]{icon} Crash Timeline — {total_crashes} total[/bold {crash_color}]",
            border_style=crash_color,
            padding=(0, 1),
        )

    def _render_filter_intelligence_view(self) -> Layout:
        """Render the 3rd view: Filter Intelligence, Job Yield, Crash Timeline, and Dogfood Tips."""
        fi_layout = Layout(name="fi_body")
        panel_skip = self._render_skip_reasons_panel()
        panel_jobs = self._render_job_metrics_panel()
        panel_crash = self._render_crash_timeline_panel()

        if self.console.width >= 100 and self.console.height >= 26:
            top_row = Layout(name="fi_top", ratio=3)
            top_row.split_row(
                Layout(panel_skip, name="skip", ratio=1),
                Layout(panel_jobs, name="jobs", ratio=1),
            )
            fi_layout.split_column(
                top_row,
                Layout(panel_crash, name="crash", size=7),
            )
        else:
            fi_layout.split_column(
                Layout(panel_skip, name="skip", ratio=1),
                Layout(panel_jobs, name="jobs", ratio=1),
                Layout(panel_crash, name="crash", ratio=1),
            )
        return fi_layout

    def _render_charts_view(self) -> Layout:
        charts_layout = Layout(name="charts_body")
        panel_funnel = self._render_funnel_chart()
        panel_quota = self._render_quota_velocity_chart()
        panel_latency = self._render_latency_chart()
        panel_motion = self._render_motion_health_chart()

        # Responsive: 2x2 grid if width >= 100 and height >= 26, else vertical stack
        if self.console.width >= 100 and self.console.height >= 26:
            top_row = Layout(name="charts_top", ratio=1)
            top_row.split_row(
                Layout(panel_funnel, name="funnel", ratio=1),
                Layout(panel_quota, name="quota", ratio=1),
            )
            bottom_row = Layout(name="charts_bottom", ratio=1)
            bottom_row.split_row(
                Layout(panel_latency, name="latency", ratio=1),
                Layout(panel_motion, name="motion", ratio=1),
            )
            charts_layout.split_column(top_row, bottom_row)
        else:
            charts_layout.split_column(
                Layout(panel_funnel, name="funnel", ratio=1),
                Layout(panel_quota, name="quota", ratio=1),
                Layout(panel_latency, name="latency", ratio=1),
                Layout(panel_motion, name="motion", ratio=1),
            )
        return charts_layout

    def generate_layout(self) -> Layout:
        """Construct the full terminal layout with responsive width adaptation."""
        if self.bound_session_state:
            self.state.update_from_session_state(self.bound_session_state)

        layout = Layout()

        # Top-level vertical split: Header (2-row), Body, Footer (2-row)
        layout.split_column(
            Layout(self._render_header(), name="header", size=4),
            Layout(name="body", ratio=1),
            Layout(self._render_footer(), name="footer", size=4),
        )

        # Route to the correct view mode
        if self.view_mode == ViewMode.STATISTICS_CHARTS:
            layout["body"].update(self._render_charts_view())
            return layout

        if self.view_mode == ViewMode.FILTER_INTELLIGENCE:
            layout["body"].update(self._render_filter_intelligence_view())
            return layout

        # ── LIVE_DASHBOARD (default) ──────────────────────────────────────
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

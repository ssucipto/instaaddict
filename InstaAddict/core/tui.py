import atexit
import logging
import os
import re
import sys
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, Optional, Tuple

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

    # Concurrency guard
    lock: threading.RLock = field(default_factory=threading.RLock)

    def elapsed_duration_str(self) -> str:
        delta = datetime.now() - self.start_time
        return str(timedelta(seconds=int(delta.total_seconds())))

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


class DashboardManager:
    """Manages Rich Live layout, refresh rate, and terminal restoration."""

    _instance: Optional["DashboardManager"] = None

    def __init__(self, console: Optional[Console] = None, refresh_rate: float = 4.0):
        self.console = console or Console(force_terminal=True, safe_box=True)
        self.state = DashboardState()
        self.refresh_rate = refresh_rate
        self.live: Optional[Live] = None
        self._active = False
        self._lock = threading.Lock()
        self.bound_session_state = None
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

    def start(self):
        with self._lock:
            if self._active:
                return
            layout = self.generate_layout()
            self.live = Live(
                layout,
                console=self.console,
                refresh_per_second=self.refresh_rate,
                screen=False,
                transient=False,
                auto_refresh=True,
            )
            self.live.start()
            self._active = True

    def stop(self):
        with self._lock:
            if not self._active:
                return
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

    def update_render(self):
        if self.live and self._active:
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

        header_text = Text()
        header_text.append(f"{icon_bot} InstaAddict AI ", style="bold bright_cyan")
        header_text.append(f"v{__version__}  │  ", style="dim cyan")
        header_text.append(f"{user_str} ", style="bold white")
        header_text.append(f"{stats_str}  │  ", style="dim white")
        header_text.append(f"{icon_dev} Device: ", style="bold yellow")
        header_text.append(f"{device_str}  │  ", style="yellow")
        header_text.append(f"{icon_time} Elapsed: ", style="bold green")
        header_text.append(f"{duration_str} (Session #{s.session_index})", style="green")

        return Panel(
            Align.center(header_text),
            style="bright_blue",
            padding=(0, 1),
        )

    def _render_stats_table(self) -> Table:
        s = self.state
        table = Table(
            expand=True,
            box=None,
            padding=(0, 1),
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

        # Uploads summary row
        uploads_total = s.uploads_ok + s.uploads_fail
        uploads_bar = ProgressBar(
            total=max(uploads_total, 1),
            completed=s.uploads_ok,
            width=None,
            complete_style="bright_green",
            finished_style="bright_green",
        )
        table.add_row(
            "Uploads (Q)",
            uploads_bar,
            f"{s.uploads_ok} OK / {s.uploads_fail} Fail",
            f"[green]{s.uploads_ok}[/green]",
        )

        return table

    def _render_activity_panel(self) -> Panel:
        s = self.state
        content = Text()

        content.append("• Active Job:   ", style="bold yellow")
        content.append(f"{s.current_job}\n", style="bright_white")

        content.append("• Current Step: ", style="bold cyan")
        content.append(f"{s.current_action}\n", style="white")

        if s.target_user:
            content.append("• Target Post:  ", style="bold magenta")
            content.append(f"@{s.target_user}", style="bright_magenta")
            if s.target_source:
                content.append(f" (source: {s.target_source})", style="dim magenta")
            content.append("\n")

        icon_cooldown = safe_glyph("⏳", "[..]")
        if s.countdown_seconds is not None and s.countdown_seconds > 0:
            content.append("• Cooldown:     ", style="bold bright_red")
            msg = s.countdown_message or "Next interaction in"
            content.append(f"{icon_cooldown} {msg} {s.countdown_seconds:02d}s\n", style="bold bright_yellow")
        else:
            content.append("• Status:       ", style="bold green")
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

        if not entries:
            log_text.append("Waiting for runtime logs...", style="dim")
        else:
            for level, timestamp, message in entries:
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
        footer_text = Text()
        footer_text.append(" [Ctrl+C] ", style="bold bright_red")
        footer_text.append("Graceful Stop  │ ", style="dim white")
        footer_text.append(" [D] ", style="bold bright_yellow")
        footer_text.append("Debug Verbose  │ ", style="dim white")
        footer_text.append(" Mode: ", style="bold cyan")
        footer_text.append("Automated Human Simulation  │ ", style="cyan")
        footer_text.append(" Safety: ", style="bold green")
        footer_text.append("Rate-Limit Guard Active", style="green")

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
            title=f"[bold bright_green]{icon_stats} Session Statistics & Limits[/bold bright_green]",
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

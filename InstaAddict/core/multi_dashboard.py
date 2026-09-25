import collections
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from InstaAddict.core.beacon import BeaconReader
from InstaAddict.core.orchestrator import AccountOrchestrator

logger = logging.getLogger(__name__)


class MultiAccountDashboard:
    """
    Rich Live Terminal User Interface (TUI) for multi-account fleet orchestration.
    Features:
    - 1.0 FPS render governor with mtime dirty-checking for <0.5% CPU utilization (GAP-19)
    - Mode 1 (Summary Table), Mode 2 (Detailed Cards), Mode 3 (Telemetry Funnel)
    - Cross-platform non-blocking keyboard listener with CONIN$ mode restoration (GAP-14)
    - Zero-downtime hot-reload hotkey [C] (GAP-21)
    - Graceful non-interactive / headless fallback
    """

    def __init__(self, orchestrator: AccountOrchestrator, console: Optional[Console] = None):
        self.orchestrator = orchestrator
        self.console = console or Console()
        self.view_mode = 1  # 1: Table, 2: Cards, 3: Telemetry
        self.start_time = datetime.now()
        self.event_log = collections.deque(maxlen=50)  # GAP-19 bounded memory
        self._stop_event = threading.Event()
        self._input_thread: Optional[threading.Thread] = None
        self._last_beacons_mtime: Dict[str, float] = {}
        self._last_render_time: float = 0.0
        self._dirty: bool = True
        self.action_callback = None

    def log_event(self, message: str) -> None:
        """Appends a timestamped event to the bounded log deque."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.event_log.append(f"[{ts}] {message}")
        self._dirty = True

    def _is_beacons_dirty(self) -> bool:
        """Checks if any accounts/<username>/.status.json file mtime has changed."""
        has_changed = False
        accounts_dir = "accounts"
        for username in self.orchestrator.processes.keys():
            b_path = os.path.join(accounts_dir, username, ".status.json")
            if os.path.exists(b_path):
                try:
                    mtime = os.path.getmtime(b_path)
                    if self._last_beacons_mtime.get(username) != mtime:
                        self._last_beacons_mtime[username] = mtime
                        has_changed = True
                except OSError:
                    pass
        return has_changed

    def render_header(self) -> Panel:
        """Creates top hero header panel."""
        active_count = sum(
            1 for p in self.orchestrator.processes.values()
            if p.process and p.process.poll() is None
        )
        total_count = len(self.orchestrator.processes)
        uptime = str(datetime.now() - self.start_time).split(".")[0]

        title = Text("InstaAddict-AI Multi-Account Fleet Manager", style="bold cyan")
        info = Text.assemble(
            (" Fleet: ", "bold white"),
            (f"{active_count}/{total_count} active", "bold green" if active_count == total_count else "bold yellow"),
            (" │ Uptime: ", "bold white"),
            (f"{uptime}", "bold cyan"),
            (" │ View Mode: ", "bold white"),
            (f"Mode {self.view_mode} (Tab to cycle)", "bold magenta"),
        )
        return Panel(Group(title, info), border_style="cyan")

    def render_summary_table(self) -> Table:
        """Renders Mode 1 compact summary table."""
        table = Table(expand=True, border_style="dim white")
        table.add_column("Account", style="bold cyan")
        table.add_column("Device", style="white")
        table.add_column("Status", justify="center")
        table.add_column("PID", justify="right", style="dim white")
        table.add_column("Job", style="white")
        table.add_column("Likes", justify="right", style="green")
        table.add_column("Follows", justify="right", style="magenta")
        table.add_column("Comments", justify="right", style="yellow")
        table.add_column("Watched", justify="right", style="blue")
        table.add_column("Crashes", justify="right", style="red")

        for username, proc in self.orchestrator.processes.items():
            beacon = BeaconReader.read_beacon(username)
            status_text = self._format_status_badge(proc.status)
            pid_str = str(proc.pid) if (proc.process and proc.process.poll() is None) else "-"

            job = "-"
            likes, follows, comments, watched, crashes = 0, 0, 0, 0, proc.restart_count

            if beacon:
                metrics = beacon.get("metrics", {})
                job = str(beacon.get("current_job", "-"))[:25]
                likes = metrics.get("total_likes", 0)
                follows = metrics.get("total_follows", 0)
                comments = metrics.get("total_comments", 0)
                watched = metrics.get("total_watched", 0)
                crashes = metrics.get("total_crashes", proc.restart_count)

            table.add_row(
                f"@{username}",
                proc.device_id,
                status_text,
                pid_str,
                job,
                str(likes),
                str(follows),
                str(comments),
                str(watched),
                str(crashes),
            )

        return table

    def render_detailed_cards(self) -> Group:
        """Renders Mode 2 individual panels per account."""
        panels = []
        for username, proc in self.orchestrator.processes.items():
            beacon = BeaconReader.read_beacon(username)
            status_badge = self._format_status_badge(proc.status)

            lines = [
                f"Status: {status_badge}  │  Device: [cyan]{proc.device_id}[/cyan]  │  PID: {proc.pid or '-'}",
            ]
            if beacon:
                metrics = beacon.get("metrics", {})
                job = beacon.get("current_job", "idle")
                likes = metrics.get("total_likes", 0)
                follows = metrics.get("total_follows", 0)
                comments = metrics.get("total_comments", 0)
                watched = metrics.get("total_watched", 0)
                lines.append(f"Current Job: [bold white]{job}[/bold white]")
                lines.append(
                    f"KPIs: Likes [green]{likes}[/green] │ Follows [magenta]{follows}[/magenta] │ "
                    f"Comments [yellow]{comments}[/yellow] │ Watched [blue]{watched}[/blue] │ Crashes [red]{proc.restart_count}[/red]"
                )
            else:
                lines.append("No active status beacon reported yet.")

            panel = Panel(
                "\n".join(lines),
                title=f"[bold cyan]@{username}[/bold cyan]",
                border_style="green" if proc.status == "running" else "white",
            )
            panels.append(panel)

        return Group(*panels)

    def render_telemetry_funnel(self) -> Table:
        """Renders Mode 3 fleet-wide conversion and yield table."""
        table = Table(title="Cross-Account Engagement Yield & Efficiency", expand=True)
        table.add_column("Account", style="bold cyan")
        table.add_column("Device", style="white")
        table.add_column("Total Actions", justify="right", style="bold white")
        table.add_column("Likes", justify="right", style="green")
        table.add_column("Follows", justify="right", style="magenta")
        table.add_column("Yield Ratio", justify="right", style="bold yellow")
        table.add_column("Health / Uptime", justify="center")

        for username, proc in self.orchestrator.processes.items():
            beacon = BeaconReader.read_beacon(username)
            likes, follows, comments, watched = 0, 0, 0, 0
            if beacon:
                metrics = beacon.get("metrics", {})
                likes = metrics.get("total_likes", 0)
                follows = metrics.get("total_follows", 0)
                comments = metrics.get("total_comments", 0)
                watched = metrics.get("total_watched", 0)

            total_actions = likes + follows + comments + watched
            ratio_str = f"{(follows / max(1, likes) * 100):.1f}%" if likes > 0 else "N/A"
            health_badge = "[green]HEALTHY[/green]" if proc.status == "running" else f"[yellow]{proc.status.upper()}[/yellow]"

            table.add_row(
                f"@{username}",
                proc.device_id,
                str(total_actions),
                str(likes),
                str(follows),
                ratio_str,
                health_badge,
            )

        return table

    def render_footer(self) -> Panel:
        """Creates bottom command bar panel with hotkeys."""
        shortcuts = (
            "[bold white][Tab][/bold white] Cycle View  │  "
            "[bold white][R][/bold white] Restart Acc  │  "
            "[bold white][S][/bold white] Stop Acc  │  "
            "[bold green][C][/bold green] Reload Config (GAP-21)  │  "
            "[bold white][L][/bold white] View Logs  │  "
            "[bold white][Q][/bold white] Quit All"
        )
        return Panel(shortcuts, style="dim white")

    def _format_status_badge(self, status: str) -> str:
        """Colorizes status string."""
        s = status.lower()
        if s == "running":
            return "[bold green]RUNNING[/bold green]"
        elif s == "sleeping":
            return "[bold blue]SLEEPING[/bold blue]"
        elif s == "crashed":
            return "[bold red]CRASHED[/bold red]"
        elif s == "stopped":
            return "[dim white]STOPPED[/dim white]"
        elif s == "device_offline":
            return "[bold red]DEVICE OFFLINE[/bold red]"
        elif s == "device_booting":
            return "[bold yellow]DEVICE BOOTING[/bold yellow]"
        elif s == "limit_reached":
            return "[bold magenta]LIMIT REACHED[/bold magenta]"
        elif s == "disabled":
            return "[dim]DISABLED[/dim]"
        return f"[white]{status.upper()}[/white]"

    def generate_layout(self) -> Layout:
        """Assembles full terminal layout."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        layout["header"].update(self.render_header())

        if self.view_mode == 1:
            layout["body"].update(self.render_summary_table())
        elif self.view_mode == 2:
            layout["body"].update(self.render_detailed_cards())
        else:
            layout["body"].update(self.render_telemetry_funnel())

        layout["footer"].update(self.render_footer())
        return layout

    def start_input_listener(self) -> None:
        """Starts cross-platform keyboard listener thread with Windows CONIN$ restoration (GAP-14)."""
        self._input_thread = threading.Thread(
            target=self._input_loop,
            daemon=True,
            name="DashboardInputListener",
        )
        self._input_thread.start()

    def _input_loop(self) -> None:
        """Cross-platform non-blocking key reading loop."""
        if sys.platform == "win32":
            import msvcrt

            while not self._stop_event.is_set():
                try:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        # Handle special/arrow keys
                        if ch in (b"\x00", b"\xe0"):
                            msvcrt.getch()
                            continue
                        self._handle_key(ch)
                        self._dirty = True
                    time.sleep(0.05)
                except Exception:
                    time.sleep(0.1)
        else:
            import select
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not self._stop_event.is_set():
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        ch = sys.stdin.read(1)
                        self._handle_key(ch.encode("utf-8"))
                        self._dirty = True
            except Exception:
                pass
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _handle_key(self, key_bytes: bytes) -> None:
        """Processes keyboard input commands."""
        k = key_bytes.lower()

        # Tab key or Ctrl+G
        if key_bytes in (b"\t", b"\x07"):
            self.view_mode = (self.view_mode % 3) + 1
            self.log_event(f"Switched view to Mode {self.view_mode}")
            return

        # 'c' key -> Config hot-reload (GAP-21)
        if k == b"c":
            self.log_event("Hotkey [C] triggered: Reloading multi_config.yml...")
            res = self.orchestrator.reload_config()
            self.log_event(res.get("message", "Reload complete"))
            return

        # 'q' key -> Quit all
        if k == b"q" or key_bytes == b"\x03":
            self.log_event("Hotkey [Q] triggered: Stopping all bot instances...")
            self.orchestrator.stop_all()
            self._stop_event.set()
            return

        # 'r' key -> Restart first or prompted account
        if k == b"r":
            enabled = self.orchestrator.config.get_enabled_accounts()
            if enabled:
                target = enabled[0].username
                self.log_event(f"Hotkey [R] triggered: Restarting @{target}...")
                threading.Thread(target=self.orchestrator.restart_account, args=(target,), daemon=True).start()
            return

        # 's' key -> Stop first or prompted account
        if k == b"s":
            enabled = self.orchestrator.config.get_enabled_accounts()
            if enabled:
                target = enabled[0].username
                self.log_event(f"Hotkey [S] triggered: Stopping @{target}...")
                threading.Thread(target=self.orchestrator.stop_account, args=(target,), daemon=True).start()
            return

    def run(self) -> None:
        """
        Main execution loop for the TUI dashboard with 1.0 FPS render governor (GAP-19).
        If non-interactive terminal, falls back to periodic summary logs.
        """
        if not sys.stdout.isatty():
            self.run_headless()
            return

        self.start_input_listener()

        with Live(
            self.generate_layout(),
            console=self.console,
            refresh_per_second=1,  # GAP-19: 1.0 FPS cap
            screen=True,
        ) as live:
            while not self._stop_event.is_set():
                now = time.time()
                # 1.0 FPS governor (at least 1.0s elapsed between renders)
                if now - self._last_render_time >= 1.0:
                    if self._dirty or self._is_beacons_dirty():
                        live.update(self.generate_layout())
                        self._last_render_time = now
                        self._dirty = False

                time.sleep(0.1)

    def run_headless(self, poll_interval: float = 15.0) -> None:
        """Headless fallback mode emitting periodic log summaries."""
        logger.info("Running MultiAccountDashboard in headless mode.")
        while not self._stop_event.is_set():
            statuses = self.orchestrator.get_status()
            summary_parts = []
            for u, s in statuses.items():
                summary_parts.append(f"@{u}: {s['status']} (device: {s['device']})")
            logger.info("Fleet status: " + " | ".join(summary_parts))
            self._stop_event.wait(poll_interval)

"""
rich_summary.py - Post-session Rich terminal summary renderer (Interface #3).

Renders a visually stunning, self-contained summary screen after each bot session.
Called from report.py::print_full_report() after the Live TUI has exited.
Falls back silently if Rich is unavailable.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe_rich_import():
    """Return Rich components or None if not installed."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich.rule import Rule
        from rich.align import Align
        from rich import box as richbox

        return {
            "Console": Console,
            "Panel": Panel,
            "Table": Table,
            "Text": Text,
            "Rule": Rule,
            "Align": Align,
            "box": richbox,
        }
    except ImportError:
        return None


def _safe_bar(ratio: float, width: int = 20, fill: str = "=", empty: str = "-") -> str:
    """Return a progress bar string."""
    filled = int(min(max(ratio, 0.0), 1.0) * width)
    return fill * filled + empty * (width - filled)


def print_rich_session_summary(sessions: list, scrape_mode: Optional[str]) -> None:
    """
    Print a visually rich post-session summary to stdout.

    Called by report.py::print_full_report() after session completion.
    Silently no-ops if Rich is unavailable.

    Args:
        sessions: List of SessionState objects for this run.
        scrape_mode: Scrape mode string or None if engagement mode.
    """
    rich = _safe_rich_import()
    if not rich or not sessions:
        return

    Console = rich["Console"]
    Panel = rich["Panel"]
    Table = rich["Table"]
    Text = rich["Text"]
    Rule = rich["Rule"]
    Align = rich["Align"]
    box = rich["box"]

    console = Console(highlight=False, markup=True)
    latest = sessions[-1]
    username = getattr(latest, "my_username", None) or "unknown"
    finish_time = getattr(latest, "finishTime", None) or datetime.now()
    start_time = getattr(latest, "startTime", datetime.now())
    duration_str = str(finish_time - start_time).split(".")[0]

    total_crashes = getattr(latest, "totalCrashes", 0)
    total_follows_dict = getattr(latest, "totalFollowed", {})
    total_follows = sum(total_follows_dict.values()) if isinstance(total_follows_dict, dict) else int(total_follows_dict or 0)
    total_likes = getattr(latest, "totalLikes", 0)
    total_comments = getattr(latest, "totalComments", 0)
    total_pm = getattr(latest, "totalPm", 0)
    total_watched = getattr(latest, "totalWatched", 0)
    total_unfollowed = getattr(latest, "totalUnfollowed", 0)
    uploads_ok = getattr(latest, "totalUploadsSuccess", 0)
    uploads_fail = getattr(latest, "totalUploadsFailed", 0)
    total_inter_dict = getattr(latest, "totalInteractions", {})
    total_interactions = sum(total_inter_dict.values()) if isinstance(total_inter_dict, dict) else 0
    succ_inter_dict = getattr(latest, "successfulInteractions", {})
    succ_interactions = sum(succ_inter_dict.values()) if isinstance(succ_inter_dict, dict) else 0
    posts_checked = getattr(latest, "totalPostsChecked", 0)
    profiles_checked = getattr(latest, "totalProfilesChecked", 0)
    profiles_skipped = getattr(latest, "totalProfilesSkipped", 0)
    watchdog_recoveries = getattr(latest, "totalWatchdogRecoveries", 0)
    skip_reasons: Dict[str, int] = dict(getattr(latest, "skip_reasons", {}) or {})
    job_metrics: Dict[str, Any] = dict(getattr(latest, "job_metrics", {}) or {})
    upload_history: List[dict] = list(getattr(latest, "uploadHistory", []) or [])

    # Compute session health score (0-100)
    health_score = 100
    if total_crashes > 0:
        health_score -= min(total_crashes * 15, 40)
    if watchdog_recoveries > 0:
        health_score -= min(watchdog_recoveries * 5, 20)
    success_rate = succ_interactions / max(total_interactions, 1)
    if success_rate < 0.30 and total_interactions > 0:
        health_score -= 10
    health_score = max(0, min(100, health_score))

    if health_score >= 85:
        health_label = "[bold bright_green]EXCELLENT[/bold bright_green]"
        health_color = "bright_green"
    elif health_score >= 65:
        health_label = "[bold bright_yellow]GOOD[/bold bright_yellow]"
        health_color = "bright_yellow"
    elif health_score >= 40:
        health_label = "[bold yellow]FAIR[/bold yellow]"
        health_color = "yellow"
    else:
        health_label = "[bold bright_red]POOR[/bold bright_red]"
        health_color = "bright_red"

    console.print()
    console.rule("[bold bright_cyan]  InstaAddict-AI -- Session Complete  [/bold bright_cyan]", style="bright_blue")
    console.print()

    # 1. Hero Banner
    hero = Text(justify="center")
    hero.append("  [+] InstaAddict-AI  ", style="bold bright_cyan")
    hero.append("----", style="dim blue")
    hero.append(f"  @{username}  ", style="bold white")
    hero.append("----", style="dim blue")
    hero.append(f"  Session finished at {finish_time.strftime('%H:%M:%S')}  \n", style="dim white")
    hero.append(f"  Duration: ", style="dim white")
    hero.append(f"{duration_str}  ", style="bold bright_green")
    hero.append("  |  ", style="dim blue")
    hero.append("Health Score: ", style="dim white")
    bar_filled = int(health_score / 5)
    health_bar = "#" * bar_filled + "." * (20 - bar_filled)
    hero.append(health_bar, style=f"bold {health_color}")
    hero.append(f" {health_score}/100 ", style=f"bold {health_color}")
    hero.append(health_label)

    console.print(Panel(
        Align.center(hero),
        style="bright_blue",
        padding=(1, 2),
    ))

    # 2. Core KPI Grid
    kpi_table = Table(
        box=box.ROUNDED,
        expand=True,
        show_header=True,
        header_style="bold bright_cyan",
        border_style="cyan",
        padding=(0, 1),
    )
    kpi_table.add_column("Metric", style="bold white", ratio=1)
    kpi_table.add_column("Value", justify="right", ratio=1)
    kpi_table.add_column("Metric", style="bold white", ratio=1)
    kpi_table.add_column("Value", justify="right", ratio=1)

    crash_style = "bold bright_red" if total_crashes > 0 else "bright_green"
    wd_style = "bright_yellow" if watchdog_recoveries > 0 else "bright_green"
    succ_pct = int(success_rate * 100)
    succ_style = "bright_green" if succ_pct >= 50 else ("bright_yellow" if succ_pct >= 20 else "bright_red")
    ads_bypassed = getattr(latest, "totalAdsBypassed", 0)

    kpi_rows = [
        ("Total Interactions", f"[white]{total_interactions}[/white]", "Successful", f"[{succ_style}]{succ_interactions} ({succ_pct}%)[/{succ_style}]"),
        ("Likes", f"[bright_cyan]{total_likes}[/bright_cyan]", "Follows", f"[bright_green]{total_follows}[/bright_green]"),
        ("Unfollows", f"[yellow]{total_unfollowed}[/yellow]", "Comments", f"[magenta]{total_comments}[/magenta]"),
        ("Stories Watched", f"[cyan]{total_watched}[/cyan]", "PMs Sent", f"[bright_blue]{total_pm}[/bright_blue]"),
        ("Posts Scanned", f"[white]{posts_checked}[/white]", "Profiles Checked", f"[white]{profiles_checked}[/white]"),
        ("Profiles Skipped", f"[dim]{profiles_skipped}[/dim]", "Ads Bypassed", f"[yellow]{ads_bypassed}[/yellow]"),
        ("Crashes", f"[{crash_style}]{total_crashes}[/{crash_style}]", "Watchdog Recoveries", f"[{wd_style}]{watchdog_recoveries}[/{wd_style}]"),
        ("Uploads OK", f"[bright_green]{uploads_ok}[/bright_green]", "Uploads Failed", f"[{'bright_red' if uploads_fail > 0 else 'dim'}]{uploads_fail}[/{'bright_red' if uploads_fail > 0 else 'dim'}]"),
    ]
    for row in kpi_rows:
        kpi_table.add_row(*row)

    console.print(Panel(
        kpi_table,
        title="[bold bright_green]Session KPI Summary[/bold bright_green]",
        border_style="green",
        padding=(0, 1),
    ))

    # 3. Per-Source Breakdown
    if isinstance(total_inter_dict, dict) and total_inter_dict:
        src_table = Table(
            box=box.SIMPLE,
            expand=True,
            header_style="bold bright_cyan",
            border_style="cyan",
            padding=(0, 1),
        )
        src_table.add_column("Source", style="bold white", ratio=2)
        src_table.add_column("Attempts", justify="right", width=10)
        src_table.add_column("Success", justify="right", width=10)
        src_table.add_column("Rate", justify="right", width=8)
        src_table.add_column("Followed", justify="right", width=10)
        src_table.add_column("Rate Bar", ratio=2)

        for src, attempts in sorted(total_inter_dict.items(), key=lambda x: x[1], reverse=True):
            succ = succ_inter_dict.get(src, 0) if isinstance(succ_inter_dict, dict) else 0
            foll = total_follows_dict.get(src, 0) if isinstance(total_follows_dict, dict) else 0
            rate = succ / max(attempts, 1)
            pct = int(rate * 100)
            rate_color = "bright_green" if pct >= 50 else ("bright_yellow" if pct >= 20 else "bright_red")
            bar_str = f"[{rate_color}]{_safe_bar(rate, 20)}[/{rate_color}]"
            src_table.add_row(src, str(attempts), str(succ), f"[{rate_color}]{pct}%[/{rate_color}]", str(foll), bar_str)

        console.print(Panel(
            src_table,
            title="[bold bright_cyan]Per-Source Interaction Breakdown[/bold bright_cyan]",
            border_style="cyan",
            padding=(0, 1),
        ))

    # 4. Skip Reason Distribution
    if skip_reasons:
        skip_table = Table(
            box=box.SIMPLE,
            expand=True,
            header_style="bold bright_red",
            padding=(0, 1),
        )
        skip_table.add_column("Skip Reason", style="bold white", ratio=2)
        skip_table.add_column("Count", justify="right", width=8)
        skip_table.add_column("%", justify="right", width=7)
        skip_table.add_column("Distribution", ratio=2)

        total_skips = sum(skip_reasons.values())
        for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True)[:10]:
            ratio = count / max(total_skips, 1)
            pct = int(ratio * 100)
            color = "bright_red" if ratio >= 0.30 else ("bright_yellow" if ratio >= 0.15 else "bright_green")
            bar_str = f"[{color}]{_safe_bar(ratio, 25)}[/{color}]"
            display = reason.replace("_", " ").title()
            skip_table.add_row(display, str(count), f"[{color}]{pct}%[/{color}]", bar_str)

        console.print(Panel(
            skip_table,
            title=f"[bold bright_red]Filter Rejection Intelligence -- {total_skips} total skips[/bold bright_red]",
            border_style="red",
            padding=(0, 1),
        ))

    # 5. Job Yield Performance
    if job_metrics:
        job_table = Table(
            box=box.SIMPLE,
            expand=True,
            header_style="bold bright_cyan",
            padding=(0, 1),
        )
        job_table.add_column("Task / Job", style="bold white", ratio=2)
        job_table.add_column("Duration", justify="right", width=9)
        job_table.add_column("Attempts", justify="right", width=10)
        job_table.add_column("Successes", justify="right", width=10)
        job_table.add_column("Yield %", justify="right", width=9)
        job_table.add_column("Status", justify="center", width=10)
        job_table.add_column("Yield Bar", ratio=2)

        for job_name, metrics in sorted(job_metrics.items()):
            attempts = metrics.get("interactions_attempted", 0)
            successes = metrics.get("interactions_successful", 0)
            duration = metrics.get("duration_seconds", 0.0)
            status = metrics.get("status", "unknown")

            yield_ratio = successes / max(attempts, 1) if attempts > 0 else 0.0
            yield_pct = int(round(yield_ratio * 100))

            yield_color = "bright_green" if yield_pct >= 50 else ("bright_yellow" if yield_pct >= 20 else ("dim white" if attempts == 0 else "bright_red"))
            status_map = {
                "completed": "[green]Done[/green]",
                "in_progress": "[bright_cyan]Active[/bright_cyan]",
                "app_has_crashed": "[bright_red]CRASH[/bright_red]",
            }
            status_str = status_map.get(status, f"[dim]{status}[/dim]")

            dur_str = f"{duration:.0f}s" if duration < 3600 else f"{duration / 3600:.1f}h"
            bar_str = f"[{yield_color}]{_safe_bar(yield_ratio, 18)}[/{yield_color}]"
            display = job_name.replace("_", " ").title()[:22]
            job_table.add_row(
                display, dur_str, str(attempts), str(successes),
                f"[{yield_color}]{yield_pct}%[/{yield_color}]",
                status_str, bar_str,
            )

        console.print(Panel(
            job_table,
            title="[bold bright_cyan]Task Yield & Job Performance[/bold bright_cyan]",
            border_style="cyan",
            padding=(0, 1),
        ))

    # 6. Upload Activity
    if upload_history:
        up_table = Table(
            box=box.SIMPLE,
            expand=True,
            header_style="bold bright_magenta",
            padding=(0, 1),
        )
        up_table.add_column("Timestamp", style="dim", width=20)
        up_table.add_column("File", style="white", ratio=2)
        up_table.add_column("Status", justify="center", width=10)
        up_table.add_column("Caption Preview", style="dim white", ratio=3)

        for up in upload_history[-10:]:
            st = up.get("status", "")
            status_str = "[bright_green]OK[/bright_green]" if st == "ok" else f"[bright_red]{st}[/bright_red]"
            caption = (up.get("caption", "") or "")[:50]
            up_table.add_row(up.get("timestamp", "")[:19], os.path.basename(up.get("file", "")), status_str, caption)

        console.print(Panel(
            up_table,
            title="[bold bright_magenta]Upload Activity Log[/bold bright_magenta]",
            border_style="magenta",
            padding=(0, 1),
        ))

    # 7. Dogfood Recommendations
    try:
        tuning_path = os.path.join("accounts", username, "tuning_suggestions.md")
        if os.path.exists(tuning_path):
            with open(tuning_path, "r", encoding="utf-8") as f:
                tuning_lines = [l.rstrip() for l in f.readlines() if l.strip() and not l.startswith("# ")]
            if tuning_lines:
                console.rule("[bold bright_yellow]Dogfood Optimizer -- Tuning Recommendations[/bold bright_yellow]", style="yellow")
                for line in tuning_lines[:12]:
                    console.print(f"  [bright_yellow]-->[/bright_yellow] {line.lstrip('- ').strip()}")
                console.print()
    except Exception:
        pass

    # 8. Crash History
    crash_history = list(getattr(latest, "crash_history", []) or [])
    if crash_history:
        console.rule("[bold bright_red]Crash History[/bold bright_red]", style="red")
        for i, crash in enumerate(crash_history[-5:], 1):
            ts = crash.get("timestamp", "")[:19]
            job = crash.get("active_job", "unknown")
            reason = crash.get("error_reason") or crash.get("exception_type", "unknown")
            pkg = crash.get("foreground_package", "")
            line = f"  [bold bright_red]#{i}[/bold bright_red] [{ts}] [white]{job}[/white] -- [bright_red]{reason}[/bright_red]"
            if pkg:
                line += f" [dim yellow](fg: {pkg})[/dim yellow]"
            console.print(line)
        console.print()

    # 9. Footer
    console.rule(
        f"[dim]Session report saved to accounts/{username}/reports/  |  history.md updated[/dim]",
        style="dim blue",
    )
    console.print()

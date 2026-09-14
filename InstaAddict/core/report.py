import logging
from datetime import datetime, timedelta

from colorama import Fore, Style

logger = logging.getLogger(__name__)


def print_full_report(sessions, scrape_mode):
    if len(sessions) > 1:
        for index, session in enumerate(sessions):
            finish_time = session.finishTime or datetime.now()
            logger.info(
                "",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            logger.info(
                f"SESSION #{index + 1}",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            logger.info(
                f"Start time: {session.startTime.strftime('%H:%M:%S (%Y/%m/%d)')}",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            logger.info(
                f"Finish time: {finish_time.strftime('%H:%M:%S (%Y/%m/%d)')}",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            duration = finish_time - session.startTime
            logger.info(
                f"Duration: {str(duration).split('.')[0]}",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            logger.info(
                f"Total interactions: {_stringify_interactions(session.totalInteractions)}",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            if scrape_mode is None:
                logger.info(
                    f"Successful interactions: {_stringify_interactions(session.successfulInteractions)}",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                logger.info(
                    f"Total followed: {_stringify_interactions(session.totalFollowed)}",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                logger.info(
                    f"Total likes: {session.totalLikes}",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                logger.info(
                    f"Total comments: {session.totalComments}",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                logger.info(
                    f"Total PM sent: {session.totalPm}",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                logger.info(
                    f"Total watched: {session.totalWatched}",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                logger.info(
                    f"Total unfollowed: {session.totalUnfollowed}",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                uploads_ok = getattr(session, "totalUploadsSuccess", 0)
                uploads_fail = getattr(session, "totalUploadsFailed", 0)
                if uploads_ok > 0 or uploads_fail > 0:
                    logger.info(
                        f"Total uploads: {uploads_ok} succeeded, {uploads_fail} failed",
                        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                    )
            else:
                logger.info(
                    f"Total scraped: {_stringify_interactions(session.totalScraped)}",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )

    logger.info(
        "",
        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
    )
    logger.info(
        "TOTAL",
        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
    )

    completed_sessions = [session for session in sessions if session.is_finished()]
    logger.info(
        f"Completed sessions: {len(completed_sessions)}",
        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
    )

    duration = timedelta(0)
    for session in sessions:
        finish_time = session.finishTime or datetime.now()
        duration += finish_time - session.startTime
    logger.info(
        f"Total duration: {str(duration).split('.')[0]}",
        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
    )

    total_interactions = {}
    total_interactions_num = 0
    successful_interactions = {}
    total_successful_interactions_num = 0
    total_followed = {}
    total_followed_num = 0
    total_scraped_num = 0
    total_scraped = {}
    for session in sessions:
        for source, count in session.totalInteractions.items():
            if total_interactions.get(source) is None:
                total_interactions[source] = count
            else:
                total_interactions[source] += count
            total_interactions_num += count
        for source, count in session.successfulInteractions.items():
            if successful_interactions.get(source) is None:
                successful_interactions[source] = count
            else:
                successful_interactions[source] += count
            total_successful_interactions_num += count

        for source, count in session.totalFollowed.items():
            if total_followed.get(source) is None:
                total_followed[source] = count
            else:
                total_followed[source] += count
            total_followed_num += count

        for source, count in session.totalScraped.items():
            if total_scraped.get(source) is None:
                total_scraped[source] = count
            else:
                total_scraped[source] += count
            total_scraped_num += count
    if scrape_mode is None:
        logger.info(
            f"Total interactions: ({total_interactions_num}) {_stringify_interactions(total_interactions)}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        logger.info(
            f"Successful interactions: ({total_successful_interactions_num}) {_stringify_interactions(successful_interactions)}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        logger.info(
            f"Total followed: ({total_followed_num}) {_stringify_interactions(total_followed)}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        total_likes = sum(session.totalLikes for session in sessions)
        logger.info(
            f"Total likes: {total_likes}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        total_comments = sum(session.totalComments for session in sessions)
        logger.info(
            f"Total comments: {total_comments}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        total_pm = sum(session.totalPm for session in sessions)
        logger.info(
            f"Total PM sent: {total_pm}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        total_watched = sum(session.totalWatched for session in sessions)
        logger.info(
            f"Total watched: {total_watched}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        total_unfollowed = sum(session.totalUnfollowed for session in sessions)
        logger.info(
            f"Total unfollowed: {total_unfollowed}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        total_uploads_ok = sum(
            getattr(session, "totalUploadsSuccess", 0) for session in sessions
        )
        total_uploads_fail = sum(
            getattr(session, "totalUploadsFailed", 0) for session in sessions
        )
        if total_uploads_ok > 0 or total_uploads_fail > 0:
            logger.info(
                f"Total uploads: {total_uploads_ok} succeeded, {total_uploads_fail} failed",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
    else:
        logger.info(
            f"Total users scraped: ({total_scraped_num}) {_stringify_interactions(total_scraped)}",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )

    save_markdown_history(sessions, scrape_mode)


def save_markdown_history(sessions, scrape_mode):
    """Automatically writes a persistent session summary and appends to history.md (never overwritten)."""
    import os

    if not sessions:
        return

    latest_session = sessions[-1]
    username = latest_session.my_username
    if not username and hasattr(latest_session, "args"):
        username = getattr(latest_session.args, "username", None)
    if not username:
        username = "default"

    account_dir = os.path.join("accounts", username)
    reports_dir = os.path.join(account_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    history_path = os.path.join(account_dir, "history.md")
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    session_report_path = os.path.join(reports_dir, f"session_{file_timestamp}.md")

    finish_time = latest_session.finishTime or datetime.now()
    duration_str = str(finish_time - latest_session.startTime).split(".")[0]

    succ_interactions = (
        sum(latest_session.successfulInteractions.values())
        if hasattr(latest_session, "successfulInteractions")
        else 0
    )
    total_followed = (
        sum(latest_session.totalFollowed.values())
        if hasattr(latest_session, "totalFollowed")
        else 0
    )
    total_likes = getattr(latest_session, "totalLikes", 0)
    total_unfollowed = getattr(latest_session, "totalUnfollowed", 0)
    total_comments = getattr(latest_session, "totalComments", 0)
    total_pm = getattr(latest_session, "totalPm", 0)
    total_watched = getattr(latest_session, "totalWatched", 0)
    total_crashes = getattr(latest_session, "totalCrashes", 0)
    uploads_ok = getattr(latest_session, "totalUploadsSuccess", 0)
    uploads_fail = getattr(latest_session, "totalUploadsFailed", 0)
    upload_str = f"{uploads_ok} ok / {uploads_fail} fail"

    # 1. Append to cumulative history.md
    write_header = (
        not os.path.exists(history_path) or os.path.getsize(history_path) == 0
    )
    try:
        with open(history_path, "a", encoding="utf-8") as f:
            if write_header:
                f.write(f"# @{username} - Session Execution History\n\n")
                f.write(
                    "This file is automatically appended at the end of every bot session to maintain non-overwritten history.\n\n"
                )
                f.write(
                    "| Timestamp | Duration | Succ. Interactions | Follows | Unfollows | Likes | Comments | PMs | Watched | Crashes | Uploads |\n"
                )
                f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
            f.write(
                f"| {timestamp_str} | {duration_str} | {succ_interactions} | {total_followed} | {total_unfollowed} | {total_likes} | {total_comments} | {total_pm} | {total_watched} | {total_crashes} | {upload_str} |\n"
            )
        logger.info(
            f"Session history appended to {history_path}",
            extra={"color": f"{Style.BRIGHT}{Fore.GREEN}"},
        )
    except Exception as e:
        logger.error(f"Failed to append session history to {history_path}: {e}")

    # 2. Write individual timestamped session report
    try:
        with open(session_report_path, "w", encoding="utf-8") as f:
            f.write(f"# Session Report: @{username}\n\n")
            f.write(f"- **Session ID**: `{getattr(latest_session, 'id', 'N/A')}`\n")
            f.write(
                f"- **Start Time**: {latest_session.startTime.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"- **Finish Time**: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Duration**: {duration_str}\n")
            f.write(f"- **Total Crashes**: {total_crashes}\n\n")

            f.write("## Interactions Summary\n")
            f.write("| Metric | Count |\n|---|---|\n")
            f.write(f"| Successful Interactions | {succ_interactions} |\n")
            f.write(f"| Followed | {total_followed} |\n")
            f.write(f"| Unfollowed | {total_unfollowed} |\n")
            f.write(f"| Likes | {total_likes} |\n")
            f.write(f"| Comments | {total_comments} |\n")
            f.write(f"| PMs Sent | {total_pm} |\n")
            f.write(f"| Watched Stories/Reels | {total_watched} |\n\n")

            # Per-source breakdown
            if (
                hasattr(latest_session, "totalInteractions")
                and latest_session.totalInteractions
            ):
                f.write("## Per-Source Interaction Breakdown\n")
                f.write(
                    "| Source | Total Attempts | Successful | Followed |\n|---|---|---|---|\n"
                )
                for src, attempts in latest_session.totalInteractions.items():
                    succ = latest_session.successfulInteractions.get(src, 0)
                    foll = latest_session.totalFollowed.get(src, 0)
                    f.write(f"| {src} | {attempts} | {succ} | {foll} |\n")
                f.write("\n")

            # Upload activity
            upload_hist = getattr(latest_session, "uploadHistory", [])
            if upload_hist:
                f.write("## Upload Activity\n")
                f.write(
                    "| Timestamp | File | Status | Caption Preview |\n|---|---|---|---|\n"
                )
                for up in upload_hist:
                    f.write(
                        f"| {up.get('timestamp', '')} | {up.get('file', '')} | {up.get('status', '')} | {up.get('caption', '')[:40]} |\n"
                    )
                f.write("\n")

        logger.info(
            f"Detailed session report saved: {session_report_path}",
            extra={"color": f"{Style.BRIGHT}{Fore.GREEN}"},
        )
    except Exception as e:
        logger.error(f"Failed to write session report {session_report_path}: {e}")

    # 3. Trigger Dogfooding Optimizer for automated parameter tuning
    try:
        from InstaAddict.core.dogfood import run_dogfood_optimization

        tuning_results = run_dogfood_optimization(username)
        if tuning_results and tuning_results.get("recommendations"):
            recs = tuning_results["recommendations"]
            if any(r["severity"] in ["HIGH", "CRITICAL"] for r in recs):
                logger.info(
                    f"Dogfood Optimizer identified tuning recommendations in accounts/{username}/tuning_suggestions.md",
                    extra={"color": f"{Style.BRIGHT}{Fore.MAGENTA}"},
                )
    except Exception as e:
        logger.debug(f"Dogfood optimization skipped or encountered error: {e}")


def print_short_report(source, session_state):
    total_likes = session_state.totalLikes
    total_comments = session_state.totalComments
    total_pm = session_state.totalPm
    total_watched = session_state.totalWatched
    total_followed = sum(session_state.totalFollowed.values())
    interactions = session_state.successfulInteractions.get(source, 0)
    logger.info(
        f"Session progress: {total_likes} likes, {total_watched} watched, {total_comments} commented, {total_pm} PM sent, {total_followed} followed, {interactions} successful interaction(s) for {source}.",
        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
    )


def print_scrape_report(source, session_state):
    total_scraped = session_state.totalScraped.get(source)
    logger.info(
        f"Session progress: {total_scraped} user(s) scraped for {source}.",
        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
    )


def _stringify_interactions(interactions):
    if len(interactions) == 0:
        return "0"

    result = ""
    for source, count in interactions.items():
        result += str(count) + " for " + source + ", "
    result = result[:-2]
    return result

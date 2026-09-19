import json
import logging
import os
import sys
from datetime import datetime, timedelta
from enum import Enum, unique

from colorama import Fore, Style
from InstaAddict.core.plugin_loader import Plugin

try:
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.dates as mdates
    from matplotlib import ticker
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    mdates = None
    ticker = None
    PdfPages = None
    plt = None

A4_WIDTH_INCHES = 8.27
A4_HEIGHT_INCHES = 11.69

logger = logging.getLogger(__name__)


class DataAnalytics(Plugin):
    """Generates a PDF analytics report of current username session data"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Generates a PDF analytics report of current username session data"
        )
        self.arguments = [
            {
                "arg": "--analytics",
                "help": "generates a PDF analytics report of current username session data",
                "action": "store_true",
                "operation": True,
            }
        ]

    def run(self, device, configs, storage, sessions, plugin):
        if not MATPLOTLIB_AVAILABLE:
            logger.error(
                "Matplotlib is required to generate analytics reports. "
                "Please install it via: pip install 'instaaddict[analytics]' or pip install matplotlib"
            )
            return

        self.args = configs.args
        self.session_state = sessions[-1]
        self.username = self.session_state.my_username
        sessions = self.load_sessions()
        # will introduce new types of report
        if not sessions:
            return

        if not os.path.exists(storage.report_path):
            os.makedirs(storage.report_path)

        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = os.path.join(
            storage.report_path, f"report_{self.username}_{timestamp}.pdf"
        )
        md_filename = filename.replace(".pdf", ".md")

        with PdfPages(filename) as pdf:
            sessions_week = self.filter_sessions(sessions, Period.LAST_WEEK)
            sessions_month = self.filter_sessions(sessions, Period.LAST_MONTH)

            self.plot_followers_growth(
                sessions_week, pdf, self.username, Period.LAST_WEEK
            )
            self.plot_followers_growth(
                sessions_month, pdf, self.username, Period.LAST_MONTH
            )
            self.plot_followers_growth(sessions, pdf, self.username, Period.ALL_TIME)

            self.plot_duration_statistics(
                sessions_week, pdf, self.username, Period.LAST_WEEK
            )
            self.plot_duration_statistics(
                sessions_month, pdf, self.username, Period.LAST_MONTH
            )
            self.plot_duration_statistics(sessions, pdf, self.username, Period.ALL_TIME)

        self.generate_markdown_report(sessions, md_filename)

        logger.info(
            f"Reports saved as {filename} and {md_filename}",
            extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
        )

    def load_sessions(self):
        path = f"accounts/{self.username}/sessions.json"
        if os.path.exists(path):
            with open(path) as json_file:
                try:
                    json_array = json.load(json_file)
                except Exception as e:
                    logger.error(
                        f"Please check {json_file.name}, it contains this error: {e}"
                    )
                    sys.exit(0)
            return json_array
        else:
            logger.warning(f"No sessions.json file found for @{self.username}")
            return None

    def plot_followers_growth(self, sessions, pdf, username, period):
        followers_count = [
            int(session.get("profile", {}).get("followers", 0)) for session in sessions
        ]
        dates = [self.get_start_time(session) for session in sessions]
        total_followed = [int(session.get("total_followed", 0)) for session in sessions]
        total_unfollowed = [
            -int(session.get("total_unfollowed", 0)) for session in sessions
        ]
        total_likes = [int(session.get("total_likes", 0)) for session in sessions]

        fig, (axes1, axes2, axes3) = plt.subplots(
            ncols=1,
            nrows=3,
            sharex="row",
            figsize=(A4_WIDTH_INCHES, A4_HEIGHT_INCHES),
            gridspec_kw={"height_ratios": [4, 1, 1]},
        )

        fig.subplots_adjust(top=0.8, hspace=0.05)

        formatter = mdates.DateFormatter("%B %dth")
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(formatter)

        axes1.plot(dates, followers_count, marker=".")
        axes1.set_ylabel("Followers")
        axes1.xaxis.grid(True, linestyle="--")
        axes1.set_title(
            f'Followers growth for account "@{self.username}".\nThis page shows correlation between followers count and GramAddict actions:\nfollows, unfollows, and likes.\n\nPeriod: {period.value}.\n',
            fontsize=12,
            x=0,
            horizontalalignment="left",
        )

        axes2.fill_between(dates, total_followed, 0, color="#00CCFF", alpha=0.4)
        axes2.fill_between(dates, total_unfollowed, 0, color="#F94949", alpha=0.4)
        axes2.set_ylabel("Follows / unfollows")
        axes2.xaxis.grid(True, linestyle="--")

        axes3.fill_between(dates, total_likes, 0, color="#78EF7B", alpha=0.4)
        axes3.set_ylabel("Likes")
        axes3.set_xlabel("Date")
        axes3.xaxis.grid(True, linestyle="--")

        pdf.savefig(fig)
        plt.close(fig)

    def filter_sessions(self, sessions, period):
        if period == Period.LAST_WEEK:
            week_ago = datetime.now() - timedelta(weeks=1)
            return list(
                filter(
                    lambda session: self.get_start_time(session) > week_ago, sessions
                )
            )
        if period == Period.LAST_MONTH:
            month_ago = datetime.now() - timedelta(days=30)
            return list(
                filter(
                    lambda session: self.get_start_time(session) > month_ago, sessions
                )
            )
        if period == Period.ALL_TIME:
            return sessions

    def get_start_time(self, session):
        return datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S.%f")

    def get_finish_time(self, session):
        finish_time = session["finish_time"]
        if finish_time == "None":
            return None
        return datetime.strptime(finish_time, "%Y-%m-%d %H:%M:%S.%f")

    def plot_duration_statistics(self, sessions, pdf, username, period):
        setups_map = {}

        for session in sessions:
            successful_interactions = session.get("successful_interactions")
            if successful_interactions is None or successful_interactions == 0:
                continue

            args = session["args"]

            likes_count = args.get("likes_count")
            if likes_count is None:
                continue

            follow_percentage = args.get("follow_percentage")
            if follow_percentage is None:
                continue

            finish_time = self.get_finish_time(session)
            if finish_time is None:
                continue

            setup = f"--likes-count {str(likes_count)}\n--follow-percentage {str(follow_percentage)}"
            start_time = self.get_start_time(session)
            time_per_interaction = (finish_time - start_time) / successful_interactions
            setups_map[setup] = time_per_interaction.total_seconds()

        def time_formatter(x, _):
            minutes = int(x // 60)
            seconds = int(x % 60)
            return (str(minutes) + "m " if minutes > 0 else "") + str(seconds) + "s"

        fig, ax = plt.subplots(
            ncols=1, nrows=1, figsize=(A4_WIDTH_INCHES, A4_HEIGHT_INCHES)
        )
        fig.subplots_adjust(top=0.8, bottom=0.2)
        plt.yticks(rotation=45, fontsize=6)
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(time_formatter))
        ax.xaxis.grid(True, linestyle="--")

        setups_map_sorted = {
            key: value
            for key, value in sorted(setups_map.items(), key=lambda item: -item[1])
        }
        setups_list = list(setups_map_sorted.keys())
        times_list = list(setups_map_sorted.values())
        ax.barh(setups_list, times_list)

        ax.set_title(
            f'Sessions duration for account "@{self.username}".\nThis page shows average time of script working per successful interaction.\nYou can obtain approximate session length by multiplying one of the\nfollowing times and your --interactions-count value.\n\nPeriod: {period.value}.\n',
            fontsize=12,
            x=0,
            horizontalalignment="left",
        )

        pdf.savefig(fig)
        plt.close(fig)

    def generate_markdown_report(self, sessions, filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# InstaAddict Comprehensive Report for @{self.username}\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Aggregate Statistics\n")
            total_sessions = len(sessions)
            total_duration = timedelta(0)
            total_crashes_all = 0
            total_uploads_all = 0
            total_uploads_failed_all = 0
            for session in sessions:
                start = self.get_start_time(session)
                finish = self.get_finish_time(session)
                if start and finish:
                    total_duration += finish - start
                total_crashes_all += session.get("total_crashes", 0)
                total_uploads_all += session.get("total_uploads_success", 0)
                total_uploads_failed_all += session.get("total_uploads_failed", 0)

            total_runtime_str = str(total_duration).split(".")[0]
            f.write(f"- **Total Sessions**: {total_sessions}\n")
            f.write(f"- **Total Runtime**: {total_runtime_str}\n")
            f.write(f"- **Total Crashes Recorded**: {total_crashes_all}\n")
            f.write(
                f"- **Total Posts Published**: {total_uploads_all} (Failed attempts: {total_uploads_failed_all})\n\n"
            )

            f.write("## Session Details\n")
            f.write(
                "| Start Time | Duration | Succ. Interactions | Follows | Unfollows | Likes | Comments | PMs | Watched | Crashes | Uploads |\n"
            )
            f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")

            all_upload_history = []
            for session in sessions:
                start_str = session.get("start_time", "")

                s_time = self.get_start_time(session)
                f_time = self.get_finish_time(session)
                duration = (
                    str(f_time - s_time).split(".")[0] if s_time and f_time else "N/A"
                )

                interactions = session.get("successful_interactions", 0)
                follows = session.get("total_followed", 0)
                unfollows = session.get("total_unfollowed", 0)
                likes = session.get("total_likes", 0)
                comments = session.get("total_comments", 0)
                pms = session.get("total_pm", 0)
                watched = session.get("total_watched", 0)
                crashes = session.get("total_crashes", 0)
                up_ok = session.get("total_uploads_success", 0)
                up_fail = session.get("total_uploads_failed", 0)
                upload_summary = f"{up_ok} ok / {up_fail} fail"

                f.write(
                    f"| {start_str} | {duration} | {interactions} | {follows} | {unfollows} | {likes} | {comments} | {pms} | {watched} | {crashes} | {upload_summary} |\n"
                )

                hist = session.get("upload_history", [])
                if hist:
                    all_upload_history.extend(hist)

            if all_upload_history:
                f.write("\n## Upload Log History\n")
                f.write("| Timestamp | File | Status | Caption Preview |\n")
                f.write("|---|---|---|---|\n")
                for u in all_upload_history:
                    f.write(
                        f"| {u.get('timestamp', '')} | {u.get('file', '')} | {u.get('status', '')} | {u.get('caption', '')[:40]} |\n"
                    )

            f.write("\n## Parameter Tuning & Analytics\n")
            f.write(
                "Use these reports along with `logs/<username>_error_trace.log` to tune your `config.yml`.\n"
            )
            f.write(
                "- **Low Successful Interactions**: Check the error trace log for UI crashes, limits reached, or outdated locators.\n"
            )
            f.write(
                "- **High Crashes**: Indicates device connectivity issues or unstable UI interactions.\n"
            )
            f.write(
                "- **Dog-Feeding**: Run the Dogfood Optimizer to automatically generate tuned parameters from this history.\n"
            )


@unique
class Period(Enum):
    LAST_WEEK = "last week"
    LAST_MONTH = "last month"
    ALL_TIME = "all time"

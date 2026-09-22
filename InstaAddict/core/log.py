import logging
import os
from logging import LogRecord
from logging.handlers import RotatingFileHandler
from uuid import uuid4

from colorama import Fore, Style
from colorama import init as init_colorama

COLORS = {
    "DEBUG": Style.DIM,
    "INFO": Fore.WHITE,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.MAGENTA,
}


# Module-level globals initialized to prevent NameError prior to configure_logger
g_session_id = None
g_log_file_name = None
g_logs_dir = "logs"
g_file_handler = None
g_error_file_handler = None
g_console_handler = None
g_tui_handler = None
g_log_file_updated = False


class ColoredFormatter(logging.Formatter):
    def __init__(self, *, fmt, datefmt=None):
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt)

    def format(self, record):
        msg = super().format(record)
        levelname = record.levelname
        if hasattr(record, "color"):
            return f"{record.color}{msg}{Style.RESET_ALL}"
        if levelname in COLORS:
            return f"{COLORS[levelname]}{msg}{Style.RESET_ALL}"
        return msg


class LoggerFilterInstaAddictOnly(logging.Filter):
    def filter(self, record: LogRecord):
        return record.name.startswith("InstaAddict")


def create_log_file_handler(filename):
    file_handler = RotatingFileHandler(
        filename,
        mode="a",
        backupCount=10,
        maxBytes=15 * 1000000,
        encoding="utf-8",
    )

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)8s | %(message)s (%(filename)s:%(lineno)d)",
            datefmt=r"[%m/%d %H:%M:%S]",
        )
    )
    file_handler.addFilter(LoggerFilterInstaAddictOnly())
    return file_handler


def create_error_log_file_handler(filename):
    file_handler = RotatingFileHandler(
        filename,
        mode="a",
        backupCount=10,
        maxBytes=15 * 1000000,
        encoding="utf-8",
    )

    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)8s | %(message)s (%(filename)s:%(lineno)d)",
            datefmt=r"[%m/%d %H:%M:%S]",
        )
    )
    # Do NOT add LoggerFilterInstaAddictOnly to error handler so that
    # external crashes (uiautomator2, adbutils, system) are captured
    return file_handler


def configure_logger(debug, username):
    global g_session_id
    global g_log_file_name
    global g_logs_dir
    global g_file_handler
    global g_error_file_handler
    global g_console_handler
    global g_log_file_updated

    console_level = logging.DEBUG if debug else logging.INFO

    g_session_id = uuid4()
    g_logs_dir = "logs"
    if username:
        g_log_file_name = f"{username}.log"
        g_log_file_updated = True
    else:
        g_log_file_name = f"{g_session_id}.log"
        g_log_file_updated = False

    init_colorama()

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console logger (limited but colored log)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s %(levelname)8s | %(message)s", datefmt="[%m/%d %H:%M:%S]"
        )
    )
    console_handler.addFilter(LoggerFilterInstaAddictOnly())
    root_logger.addHandler(console_handler)
    g_console_handler = console_handler

    # File logger (full raw log)
    if not os.path.exists(g_logs_dir):
        os.makedirs(g_logs_dir)
    g_file_handler = create_log_file_handler(f"{g_logs_dir}/{g_log_file_name}")
    root_logger.addHandler(g_file_handler)

    error_log_name = g_log_file_name.replace(".log", "_error_trace.log")
    g_error_file_handler = create_error_log_file_handler(
        f"{g_logs_dir}/{error_log_name}"
    )
    root_logger.addHandler(g_error_file_handler)

    def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        import sys

        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        try:
            from InstaAddict.core.tui import DashboardManager

            if DashboardManager.is_active():
                DashboardManager.get_instance().stop()
                disable_tui_logging()
        except Exception:
            pass

        try:
            root_logger.critical(
                "Uncaught fatal exception:", exc_info=(exc_type, exc_value, exc_traceback)
            )
        except (KeyboardInterrupt, SystemExit):
            sys.exit(0)
        except Exception:
            pass

        try:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        except Exception:
            pass

    import sys

    sys.excepthook = handle_uncaught_exception

    init_logger = logging.getLogger(__name__)
    init_logger.debug(f"Initial log file: {g_logs_dir}/{g_log_file_name}")
    init_logger.debug(f"Initial error log file: {g_logs_dir}/{error_log_name}")


def get_log_file_config():
    return g_log_file_name, g_logs_dir, g_file_handler, g_session_id


def is_log_file_updated():
    return g_log_file_updated


def update_log_file_name(username: str):
    old_log_file_name, logs_dir, file_handler, _ = get_log_file_config()
    old_full_filename = f"{logs_dir}/{old_log_file_name}"

    old_error_log_file_name = old_log_file_name.replace(".log", "_error_trace.log")
    old_error_full_filename = f"{logs_dir}/{old_error_log_file_name}"

    current_logger = logging.getLogger(__name__)
    if not username:
        current_logger.error(f"No username found, using log file {old_full_filename}")
        return
    named_log_file_name = f"{username}.log"
    named_full_filename = f"{logs_dir}/{named_log_file_name}"

    named_error_log_file_name = f"{username}_error_trace.log"
    named_error_full_filename = f"{logs_dir}/{named_error_log_file_name}"

    rollover = bool(os.path.isfile(named_full_filename))
    named_file_handler = create_log_file_handler(named_full_filename)
    if rollover:
        named_file_handler.doRollover()

    error_rollover = bool(os.path.isfile(named_error_full_filename))
    named_error_file_handler = create_error_log_file_handler(named_error_full_filename)
    if error_rollover:
        named_error_file_handler.doRollover()

    # copy existing runtime logs (uidd4.log) to named log file (username.log)
    if os.path.exists(old_full_filename):
        with open(old_full_filename, "r", encoding="utf-8") as unnamed_file, open(
            named_full_filename, "a", encoding="utf-8"
        ) as named_file:
            for line in unnamed_file:
                named_file.write(line)

    if os.path.exists(old_error_full_filename):
        with open(
            old_error_full_filename, "r", encoding="utf-8"
        ) as unnamed_error_file, open(
            named_error_full_filename, "a", encoding="utf-8"
        ) as named_error_file:
            for line in unnamed_error_file:
                named_error_file.write(line)

    root_logger = logging.getLogger()
    root_logger.removeHandler(file_handler)
    root_logger.addHandler(named_file_handler)

    global g_error_file_handler
    if g_error_file_handler:
        root_logger.removeHandler(g_error_file_handler)
    root_logger.addHandler(named_error_file_handler)

    current_logger = logging.getLogger(__name__)
    current_logger.debug(f"Updated log file: {named_full_filename}")
    current_logger.debug(f"Updated error log file: {named_error_full_filename}")

    # Explicitly close old handlers before unlinking files to prevent Windows PermissionError
    try:
        file_handler.close()
    except Exception as e:
        current_logger.debug(f"Error closing old file handler: {e}")

    try:
        if g_error_file_handler:
            g_error_file_handler.close()
    except Exception as e:
        current_logger.debug(f"Error closing old error file handler: {e}")

    try:
        if os.path.exists(old_full_filename):
            os.remove(old_full_filename)
    except Exception as e:
        current_logger.debug(
            f"Failed to remove old file: {old_full_filename}. Exception: {e}"
        )

    try:
        if os.path.exists(old_error_full_filename):
            os.remove(old_error_full_filename)
    except Exception as e:
        current_logger.debug(
            f"Failed to remove old error file: {old_error_full_filename}. Exception: {e}"
        )

    global g_log_file_name
    global g_file_handler
    global g_log_file_updated
    g_log_file_name = named_log_file_name
    g_file_handler = named_file_handler
    g_error_file_handler = named_error_file_handler
    g_log_file_updated = True


def enable_tui_logging(dashboard_manager=None):
    """Route logs through TuiLogHandler and detach raw console StreamHandler."""
    global g_tui_handler
    root_logger = logging.getLogger()

    if g_console_handler and g_console_handler in root_logger.handlers:
        root_logger.removeHandler(g_console_handler)

    if g_tui_handler is None:
        from InstaAddict.core.tui import DashboardManager, TuiLogHandler

        mgr = dashboard_manager or DashboardManager.get_instance()
        g_tui_handler = TuiLogHandler(mgr.state)
        level = g_console_handler.level if g_console_handler else logging.INFO
        g_tui_handler.setLevel(level)
        g_tui_handler.setFormatter(logging.Formatter(fmt="%(message)s"))
        g_tui_handler.addFilter(LoggerFilterInstaAddictOnly())

    if g_tui_handler not in root_logger.handlers:
        root_logger.addHandler(g_tui_handler)


def disable_tui_logging():
    """Detach TuiLogHandler and reattach standard console StreamHandler."""
    root_logger = logging.getLogger()

    if g_tui_handler and g_tui_handler in root_logger.handlers:
        root_logger.removeHandler(g_tui_handler)

    if g_console_handler and g_console_handler not in root_logger.handlers:
        root_logger.addHandler(g_console_handler)

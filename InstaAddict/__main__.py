import argparse
import os
os.environ.setdefault("MPLBACKEND", "Agg")
from os import getcwd, path

from InstaAddict import __version__
from InstaAddict.core.bot_flow import start_bot
from InstaAddict.core.download_from_github import download_from_github


def cmd_init(args):
    if args.account_name is not None:
        print(f"Script launched in {getcwd()}, files will be available there.")
        for username in args.account_name:
            if not path.exists("./run.py"):
                print("Creating run.py ...")
                download_from_github(
                    "https://github.com/ssucipto/instaaddict/blob/master/run.py"
                )
            if not path.exists(f"./accounts/{username}"):
                print(
                    f"Creating 'accounts/{username}' folder with a config starting point inside. You have to edit these files according with https://docs.gramaddict.org/#/configuration"
                )
                download_from_github(
                    "https://github.com/ssucipto/instaaddict/tree/master/config-examples",
                    output_dir=f"accounts/{username}",
                    flatten=True,
                )
            else:
                print(f"'accounts/{username}' folder already exists, skip.")
                continue
            with open(f"./accounts/{username}/config.yml", "r+", encoding="utf-8") as f:
                config = f.read()
                f.seek(0)
                config_fixed = config.replace("myusername", username)
                f.write(config_fixed)
    else:
        print("You have to provide at last one account name..")


def cmd_run(args):
    start_bot()


def cmd_dump(args):
    import os
    import shutil
    import time

    import uiautomator2 as u2
    from colorama import Fore, Style

    if not args.no_kill:
        os.popen("adb shell pkill atx-agent").close()
    try:
        d = u2.connect(args.device)
    except RuntimeError as err:
        raise SystemExit(err)

    def dump_hierarchy(device, path):
        xml_dump = device.dump_hierarchy()
        with open(path, "w", encoding="utf-8") as outfile:
            outfile.write(xml_dump)

    def make_archive(name):
        os.chdir("dump")
        shutil.make_archive(base_name=f"screen_{name}", format="zip", root_dir="cur")
        shutil.rmtree("cur")

    os.makedirs("dump/cur", exist_ok=True)
    d.screenshot("dump/cur/screenshot.png")
    dump_hierarchy(d, "dump/cur/hierarchy.xml")
    archive_name = int(time.time())
    make_archive(archive_name)
    print(
        Fore.GREEN
        + Style.BRIGHT
        + "\nCurrent screen dump generated successfully! Please, send me this file:"
    )
    print(Fore.BLUE + Style.BRIGHT + f"{os.getcwd()}\\screen_{archive_name}.zip")


def cmd_multi(args):
    import json
    import sys
    from datetime import datetime
    from InstaAddict.core.multi_config import MultiAccountConfig, MultiConfigValidationError
    from InstaAddict.core.orchestrator import AccountOrchestrator
    from InstaAddict.core.beacon import BeaconReader

    config_path = getattr(args, "config", None) or "multi_config.yml"

    # Handle --status query without spawning orchestrator
    if getattr(args, "status", False):
        if not os.path.exists(config_path):
            print(f"Error: Multi-account config file '{config_path}' not found.")
            sys.exit(1)
        try:
            cfg = MultiAccountConfig.load(config_path)
            print(f"\nInstaAddict-AI Fleet Status ({config_path}):")
            print("-" * 75)
            for acc in cfg.accounts:
                beacon = BeaconReader.read_beacon(acc.username)
                status = beacon.get("status", "offline") if beacon else ("enabled" if acc.enabled else "disabled")
                likes = beacon.get("metrics", {}).get("total_likes", "-") if beacon else "-"
                follows = beacon.get("metrics", {}).get("total_follows", "-") if beacon else "-"
                print(f"@{acc.username:<20} Device: {acc.device_id:<18} Status: {status:<15} Likes: {likes:<5} Follows: {follows}")
            print("-" * 75)
            return
        except Exception as e:
            print(f"Error reading fleet status: {e}")
            sys.exit(1)

    # Handle --reload signal to running orchestrator
    if getattr(args, "reload", False):
        pid_file = os.path.join("logs", "orchestrator", "orchestrator.pid")
        if not os.path.exists(pid_file):
            print("No active AccountOrchestrator found running.")
            sys.exit(1)
        cmd_file = os.path.join("logs", "orchestrator", ".cmd.json")
        try:
            with open(cmd_file, "w", encoding="utf-8") as f:
                json.dump({"cmd": "reload", "timestamp": datetime.now().isoformat()}, f)
            print("Reload signal dispatched to running orchestrator.")
        except Exception as e:
            print(f"Failed to send reload signal: {e}")
        return

    # Handle --stop signal
    if getattr(args, "stop", None) is not None:
        target_user = args.stop
        if target_user:
            clean_u = target_user.lstrip("@").strip()
            stop_file = os.path.join("accounts", clean_u, ".stop")
            os.makedirs(os.path.dirname(stop_file), exist_ok=True)
            with open(stop_file, "w", encoding="utf-8") as f:
                f.write(f"STOP {datetime.now().isoformat()}\n")
            print(f"Stop signal sent to @{clean_u}.")
        else:
            cmd_file = os.path.join("logs", "orchestrator", ".cmd.json")
            with open(cmd_file, "w", encoding="utf-8") as f:
                json.dump({"cmd": "stop_all", "timestamp": datetime.now().isoformat()}, f)
            print("Stop all signal dispatched to running orchestrator.")
        return

    # Regular orchestrator startup
    try:
        cfg = MultiAccountConfig.load(config_path)
    except FileNotFoundError:
        print(f"Error: Config file '{config_path}' not found. Please create it or copy from config-examples/multi_config.yml")
        sys.exit(1)
    except MultiConfigValidationError as e:
        print(f"Configuration Validation Error: {e}")
        sys.exit(1)

    orchestrator = AccountOrchestrator(cfg)

    # Check --only
    only_user = getattr(args, "only", None)
    if only_user:
        acc = cfg.get_account(only_user)
        if not acc:
            print(f"Error: Account @{only_user} not found in {config_path}.")
            sys.exit(1)
        print(f"Starting only @{only_user} under orchestrator...")
        orchestrator.start_account(acc.username)
    else:
        orchestrator.start_all()

    # Launch dashboard or headless loop
    from InstaAddict.core.multi_dashboard import MultiAccountDashboard
    dashboard = MultiAccountDashboard(orchestrator)
    if getattr(args, "no_tui", False) or not sys.stdout.isatty():
        dashboard.run_headless()
    else:
        dashboard.run()


_commands = [
    dict(
        action=cmd_init,
        command="init",
        help="creates your account folder under accounts with files for configuration",
        flags=[
            dict(
                args=["account_name"],
                nargs="+",
                help="instagram account name to initialize",
            ),
        ],
    ),
    dict(
        action=cmd_run,
        command="run",
        help="start the bot!",
        flags=[
            dict(args=["--config"], nargs="?", help="provide the config.yml path"),
        ],
    ),
    dict(
        action=cmd_dump,
        command="dump",
        help="dump current screen",
        flags=[
            dict(
                args=["--device"],
                nargs=None,
                default=None,
                help="provide the device name if more then one connected",
            ),
            dict(
                args=["--no-kill"],
                action="store_true",
                help="don't kill the uia2 demon",
            ),
        ],
    ),
    dict(
        action=cmd_multi,
        command="multi",
        help="manage multiple Instagram accounts simultaneously",
        flags=[
            dict(args=["--config"], nargs="?", default="multi_config.yml", help="provide the multi_config.yml path"),
            dict(args=["--only"], nargs="?", default=None, help="run only a specific account under orchestrator"),
            dict(args=["--status"], action="store_true", help="query and display fleet status then exit"),
            dict(args=["--stop"], nargs="?", const="", default=None, help="send stop signal to running orchestrator or specific account"),
            dict(args=["--restart"], nargs="?", default=None, help="send restart signal to specific account"),
            dict(args=["--reload"], action="store_true", help="trigger zero-downtime config hot-reload on running orchestrator (GAP-21)"),
            dict(args=["--no-tui"], action="store_true", help="run in headless mode without TUI"),
        ],
    ),
]


def main() -> None:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] not in ("init", "run", "dump", "multi", "-h", "--help", "-v", "--version"):
        sys.argv.insert(1, "run")

    parser = argparse.ArgumentParser(
        prog="InstaAddict-AI",
        description="free human-like Instagram bot",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} {__version__}"
    )
    subparser = parser.add_subparsers(dest="subparser")
    actions = {}
    for c in _commands:
        cmd_name = c["command"]
        actions[cmd_name] = c["action"]
        sp = subparser.add_parser(
            cmd_name,
            help=c.get("help"),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        for f in c.get("flags", []):
            args = f.get("args")
            if not args:
                args = ["-" * min(2, len(n)) + n for n in f["name"]]
            kwargs = f.copy()
            kwargs.pop("name", None)
            kwargs.pop("args", None)
            kwargs.pop("run", None)
            sp.add_argument(*args, **kwargs)

    args, _ = parser.parse_known_args()

    if args.subparser:
        actions[args.subparser](args)
        return

    parser.print_help()


if __name__ == "__main__":
    main()

import logging
import os
import random
import sys
from datetime import datetime, timedelta
from time import sleep

from colorama import Fore, Style

from InstaAddict import __tested_ig_version__
from InstaAddict.core.config import Config
from InstaAddict.core.device_facade import create_device, get_device_info
from InstaAddict.core.filter import Filter
from InstaAddict.core.filter import load_config as load_filter
from InstaAddict.core.interaction import load_config as load_interaction
from InstaAddict.core.log import (
    configure_logger,
    disable_tui_logging,
    enable_tui_logging,
    is_log_file_updated,
    update_log_file_name,
)
from InstaAddict.core.navigation import check_if_english
from InstaAddict.core.tui import DashboardManager
from InstaAddict.core.persistent_list import PersistentList
from InstaAddict.core.report import print_full_report
from InstaAddict.core.session_state import SessionState, SessionStateEncoder
from InstaAddict.core.storage import Storage
from InstaAddict.core.watchdog import BotWatchdog
from InstaAddict.core.utils import (
    ask_for_a_donation,
    can_repeat,
    check_adb_connection,
    check_if_updated,
    check_screen_timeout,
    close_instagram,
    config_examples,
    countdown,
    get_instagram_version,
    get_value,
    head_up_notifications,
    kill_atx_agent,
    random_sleep,
)
from InstaAddict.core.utils import load_config as load_utils
from InstaAddict.core.utils import (
    move_usernames_to_accounts,
    open_instagram,
    pre_post_script,
    print_telegram_reports,
    restart_atx_agent,
    save_crash,
    set_time_delta,
    show_ending_conditions,
    stop_bot,
    wait_for_next_session,
)
from InstaAddict.core.views import (
    AccountView,
    ProfileView,
    TabBarView,
    UniversalActions,
)
from InstaAddict.core.views import load_config as load_views


def start_bot(**kwargs):
    # Logging initialization
    logger = logging.getLogger(__name__)

    # Pre-Load Config
    configs = Config(first_run=True, **kwargs)
    configure_logger(configs.debug, configs.username)
    if not kwargs:
        if "--config" not in configs.args:
            logger.info(
                "It's strongly recommend to use a config.yml file. Follow these links for more details: https://docs.gramaddict.org/#/configuration and https://github.com/ssucipto/instaaddict/tree/master/config-examples",
                extra={"color": f"{Fore.GREEN}{Style.BRIGHT}"},
            )
            sleep(3)

    # Config-example hint
    config_examples()

    # Check for updates
    check_if_updated()

    # Move username folders to a main directory -> accounts
    if "--move-folders-in-accounts" in configs.args:
        move_usernames_to_accounts()

    # Global Variables
    sessions = PersistentList("sessions", SessionStateEncoder)

    # Load Config
    configs.load_plugins()
    configs.parse_args()
    # Some plugins need config values without being passed
    # through. Because we do a weird config/argparse hybrid,
    # we need to load the configs in a weird way
    load_filter(configs)
    load_interaction(configs)
    load_utils(configs)
    load_views(configs)

    if not configs.args or not check_adb_connection():
        return

    if len(configs.enabled) < 1:
        logger.error(
            "You have to specify one of these actions: " + ", ".join(configs.actions)
        )
        return
    device = create_device(configs.device_id, configs.app_id)
    session_state = None
    if str(configs.args.total_sessions) != "-1":
        total_sessions = get_value(configs.args.total_sessions, None, -1)
    else:
        total_sessions = -1

    # init
    analytics_at_end = False
    telegram_reports_at_end = False
    followers_now = None
    following_now = None

    # Determine whether TUI is enabled
    use_tui = (
        not getattr(configs.args, "no_tui", False)
        and (getattr(configs.args, "tui", False) or sys.stdout.isatty())
        and os.environ.get("INSTAADDICT_NO_TUI", "0") != "1"
    )
    dashboard_manager = DashboardManager.get_instance()
    if use_tui:
        dashboard_manager.state.device_id = configs.device_id
        dashboard_manager.state.total_sessions = total_sessions
        dashboard_manager.start()
        enable_tui_logging(dashboard_manager)

    # Initialize and start autonomous watchdog
    watchdog = BotWatchdog.get_instance(
        device_id=configs.device_id,
        app_id=configs.app_id,
    )
    watchdog.start()

    while True:
        if use_tui and not dashboard_manager.is_active():
            dashboard_manager.start()
            enable_tui_logging(dashboard_manager)
        set_time_delta(configs.args)
        inside_working_hours, time_left = SessionState.inside_working_hours(
            configs.args.working_hours, configs.args.time_delta_session
        )
        if not inside_working_hours:
            watchdog.pause()
            wait_for_next_session(time_left, session_state, sessions, device)
            watchdog.resume()
        pre_post_script(path=configs.args.pre_script)
        if getattr(configs.args, "telegram_inbox", False) or getattr(
            configs.args, "telegram_reports", False
        ):
            try:
                from InstaAddict.plugins.telegram import check_telegram_inbox

                check_telegram_inbox(configs.args.username)
            except Exception as e:
                logger.debug(f"check_telegram_inbox loop error: {e}")
        if configs.args.restart_atx_agent:
            restart_atx_agent(device)
        get_device_info(device)
        session_state = SessionState(configs)
        session_state.set_limits_session()
        SessionState.set_active(session_state)
        sessions.append(session_state)
        watchdog.resume()
        watchdog.heartbeat("session_init", "Session initialized")
        if dashboard_manager.is_active():
            dashboard_manager.bind_session_state(session_state)
            dashboard_manager.state.session_index = len(sessions)
            dashboard_manager.state.status_message = "RUNNING"
            dashboard_manager.update_render()
        check_screen_timeout()
        device.wake_up()
        head_up_notifications(enabled=False)
        logger.info(
            "-------- START: "
            + str(session_state.startTime.strftime("%H:%M:%S - %Y/%m/%d"))
            + " --------",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )

        if not device.get_info()["screenOn"]:
            device.press_power()
        if device.is_screen_locked():
            device.unlock()
            if device.is_screen_locked():
                logger.error(
                    "Can't unlock your screen. There may be a passcode on it. If you would like your screen to be turned on and unlocked automatically, please remove the passcode."
                )
                stop_bot(device, sessions, session_state, was_sleeping=False)

        logger.info("Device screen ON and unlocked.")
        if open_instagram(device):
            try:
                running_ig_version = get_instagram_version()
                logger.info(f"Instagram version: {running_ig_version}")
                if tuple(running_ig_version.split(".")) > tuple(
                    __tested_ig_version__.split(".")
                ):
                    logger.warning(
                        f"You have a newer version of IG then the one tested! (Tested version: {__tested_ig_version__}).",
                        extra={"color": f"{Style.BRIGHT}"},
                    )
                    logger.warning(
                        "Using an untested version of IG would cause unexpected behavior because some elements in the user interface may have been changed. Any crashes that occur with an untested version are not taken into account."
                    )
                    if not configs.args.allow_untested_ig_version:
                        logger.warning(
                            "If you press ENTER, you are aware of this and will not ask for support in case of a crash."
                        )
                        logger.warning(
                            "If you want to avoid pressing ENTER next run, add allow-untested-ig-version: true in your config.yml file. (read the docs for more info)"
                        )
                        was_tui = dashboard_manager.is_active()
                        if was_tui:
                            dashboard_manager.stop()
                            disable_tui_logging()
                        try:
                            input()
                        except KeyboardInterrupt:
                            logger.info("Bot aborted by user at version prompt.")
                            sys.exit(0)
                        except EOFError:
                            logger.info(
                                "Proceeding with untested IG version (non-interactive session detected)."
                            )
                        finally:
                            if was_tui:
                                dashboard_manager.start()
                                enable_tui_logging(dashboard_manager)
                    else:
                        logger.info(
                            "Proceeding with untested IG version (allow-untested-ig-version is enabled)."
                        )

            except Exception as e:
                logger.error(f"Error retrieving the IG version. Exception: {e}")

            UniversalActions.close_keyboard(device)
        else:
            break
        profile_view = ProfileView(device)
        account_view = AccountView(device)
        tab_bar_view = TabBarView(device)
        try:
            account_view.navigate_to_main_account()
            check_if_english(device)
            if configs.args.username is not None:
                success = account_view.changeToUsername(configs.args.username)
                if not success:
                    logger.error(
                        f"Not able to change to {configs.args.username}, abort!"
                    )
                    save_crash(device)
                    device.back()
                    break
            account_view.refresh_account()
            (
                session_state.my_username,
                session_state.my_posts_count,
                session_state.my_followers_count,
                session_state.my_following_count,
            ) = profile_view.getProfileInfo()
            if dashboard_manager.is_active():
                dashboard_manager.state.username = session_state.my_username
                dashboard_manager.state.followers_count = str(session_state.my_followers_count or 0)
                dashboard_manager.state.following_count = str(session_state.my_following_count or 0)
                dashboard_manager.state.posts_count = str(session_state.my_posts_count or 0)
                dashboard_manager.update_render()
        except Exception as e:
            logger.error(f"Exception: {e}")
            save_crash(device)
            break

        if (
            session_state.my_username is None
            or session_state.my_posts_count is None
            or session_state.my_followers_count is None
            or session_state.my_following_count is None
        ):
            logger.critical(
                "Could not get one of the following from your profile: username, # of posts, # of followers, # of followings. This is typically due to a soft-ban. Review the crash screenshot to see if this is the case."
            )
            logger.critical(
                f"Username: {session_state.my_username}, Posts: {session_state.my_posts_count}, Followers: {session_state.my_followers_count}, Following: {session_state.my_following_count}"
            )
            save_crash(device)
            stop_bot(device, sessions, session_state)

        if not is_log_file_updated():
            try:
                update_log_file_name(session_state.my_username)
            except Exception as e:
                logger.error(
                    f"Failed to update log file name. Will continue anyway. {e}"
                )
        report_string = f"Hello, @{session_state.my_username}! You have {session_state.my_followers_count} followers and {session_state.my_following_count} followings so far."
        logger.info(report_string, extra={"color": f"{Style.BRIGHT}{Fore.GREEN}"})
        if configs.args.repeat:
            logger.info(
                f"You have {total_sessions + 1 - len(sessions) if total_sessions > 0 else 'infinite'} session(s) left. You can stop the bot by pressing CTRL+C in console.",
                extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
            )
            sleep(3)
        only_upload_requested = bool(
            getattr(configs.args, "only_upload", False)
            or getattr(configs.args, "upload_now", False)
        )
        if only_upload_requested:
            logger.info(
                "On-demand upload mode requested (--only-upload). Restricting session solely to upload-posts.",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            jobs_list = ["upload-posts"]
            total_sessions = 1
        elif configs.args.shuffle_jobs:
            jobs_list = random.sample(configs.enabled, len(configs.enabled))
        else:
            jobs_list = configs.enabled

        if not only_upload_requested:
            if "analytics" in jobs_list:
                jobs_list.remove("analytics")
                if configs.args.analytics:
                    analytics_at_end = True
            if "telegram-reports" in jobs_list:
                jobs_list.remove("telegram-reports")
                if configs.args.telegram_reports:
                    telegram_reports_at_end = True
            if "telegram-inbox" in jobs_list:
                jobs_list.remove("telegram-inbox")
            if "upload-posts" in jobs_list:
                jobs_list.remove("upload-posts")
                jobs_list.insert(0, "upload-posts")
        print_limits = True
        unfollow_jobs = [x for x in jobs_list if "unfollow" in x]
        logger.info(
            f"There is/are {len(jobs_list)-len(unfollow_jobs)} active-job(s) and {len(unfollow_jobs)} unfollow-job(s) scheduled for this session."
        )
        storage = Storage(session_state.my_username)
        filters = Filter(storage)
        show_ending_conditions()
        if not configs.args.debug and not only_upload_requested:
            countdown(10, "Bot will start in: ")
        for plugin in jobs_list:
            watchdog.heartbeat(f"job:{plugin}", f"Starting {plugin}")
            inside_working_hours, time_left = SessionState.inside_working_hours(
                configs.args.working_hours, configs.args.time_delta_session
            )
            if not inside_working_hours:
                logger.info(
                    "Outside of working hours. Ending session.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                break
            (
                active_limits_reached,
                unfollow_limit_reached,
                actions_limit_reached,
            ) = session_state.check_limit(
                limit_type=session_state.Limit.ALL, output=print_limits
            )
            if actions_limit_reached:
                logger.info(
                    "At last one of these limits has been reached: interactions/successful or scraped. Ending session.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                break
            if profile_view.getUsername(error=False) != session_state.my_username:
                logger.debug("Not in your main profile. Initiating recovery...")
                # Immediate pre-recovery popup sweep (CO-028 / CO-030)
                UniversalActions.dismiss_dialog(device)

                resource_id = getattr(device, "ResourceID", None)
                if resource_id is None or isinstance(resource_id, type):
                    action_bar_back = f"{configs.args.app_id}:id/action_bar_button_back"
                else:
                    action_bar_back = getattr(
                        resource_id,
                        "ACTION_BAR_BUTTON_BACK",
                        f"{configs.args.app_id}:id/action_bar_button_back",
                    )

                on_profile = False
                for attempt in range(4):
                    # Sweep any blocking dialogs before tab navigation
                    UniversalActions.dismiss_dialog(device)

                    # Back up to 3 times if tab bar is not visible
                    for _ in range(3):
                        if tab_bar_view.is_tab_bar_visible():
                            break
                        back_btn = device.find(resourceIdMatches=action_bar_back)
                        if back_btn.exists():
                            logger.debug("Tapping action_bar_button_back to exit search/subscreen.")
                            back_btn.click()
                        else:
                            logger.debug("Tab bar not visible, go back.")
                            device.back()
                        random_sleep(1, 2, modulable=False)
                        UniversalActions.dismiss_dialog(device)

                    tab_bar_view.navigateToProfile()
                    if profile_view.getUsername(error=False) == session_state.my_username:
                        on_profile = True
                        break

                    logger.debug(f"Profile recovery attempt {attempt + 1}/4 did not reach profile.")

                    # Escalated recovery tiers (CO-031 / CO-033)
                    if attempt == 0:
                        device.back()
                        random_sleep(1, 2, modulable=False)
                        UniversalActions.dismiss_dialog(device)
                    elif attempt == 1:
                        # Try navigating to Home first, then Profile
                        tab_bar_view.navigateToHome()
                        random_sleep(1, 2, modulable=False)
                        UniversalActions.dismiss_dialog(device)
                        tab_bar_view.navigateToProfile()
                        if profile_view.getUsername(error=False) == session_state.my_username:
                            on_profile = True
                            break
                    elif attempt == 2:
                        # Nuclear / Self-healing recovery: Clean restart of Instagram!
                        logger.warning(
                            "Persistent navigation deadlock detected. Executing self-healing app restart...",
                            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                        )
                        UniversalActions.recover_stuck_screen(device, configs.args.app_id)
                        tab_bar_view.navigateToProfile()
                        if profile_view.getUsername(error=False) == session_state.my_username:
                            on_profile = True
                            break

                if not on_profile:
                    logger.warning(
                        f"Could not reach {session_state.my_username}'s profile after 4 recovery attempts. "
                        "Skipping this job to avoid running it on the wrong screen."
                    )
                    continue

            # Check for user-triggered task skip request via TUI hotkey [S]/[N]
            if (
                dashboard_manager.is_active()
                and dashboard_manager.state.consume_skip_task_request()
            ):
                logger.warning(
                    f"[TUI] Skipping job '{plugin}' triggered by user shortcut ([S]/[N]). Advancing to next task...",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                continue

            # Check for user-triggered on-demand upload request via TUI hotkey [U]
            if (
                dashboard_manager.is_active()
                and dashboard_manager.state.consume_upload_request()
            ):
                logger.info(
                    "[TUI] Executing on-demand queue photo upload triggered by user hotkey [U]...",
                    extra={"color": f"{Style.BRIGHT}{Fore.MAGENTA}"},
                )
                try:
                    from InstaAddict.plugins.upload_posts import UploadPostsPlugin

                    uploader = (
                        configs.actions.get("upload-posts")
                        or UploadPostsPlugin()
                    )
                    orig_force = getattr(configs.args, "upload_force", False)
                    configs.args.upload_force = True
                    dashboard_manager.state.update_activity(
                        action="Uploading queued photo now...",
                    )
                    dashboard_manager.update_render(force=True)
                    try:
                        uploader.run(
                            device, configs, storage, sessions, filters, "upload-posts"
                        )
                    finally:
                        configs.args.upload_force = orig_force
                    dashboard_manager.state.refresh_queue_status(session_state.my_username)
                    dashboard_manager.update_render(force=True)
                except Exception as e:
                    logger.error(f"[TUI] Failed executing on-demand upload: {e}")

            if plugin in unfollow_jobs:
                if configs.args.scrape_to_file is not None:
                    logger.warning(
                        "Scraping in unfollow-jobs doesn't make any sense. SKIP. "
                    )
                    continue
                if unfollow_limit_reached:
                    logger.warning(
                        f"Can't perform {plugin} job because the unfollow limit has been reached. SKIP."
                    )
                    print_limits = None
                    continue
                logger.info(
                    f"Current unfollow-job: {plugin}",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
                configs.actions[plugin].run(
                    device, configs, storage, sessions, filters, plugin
                )
                watchdog.heartbeat(f"job:{plugin}_done", f"Completed {plugin}")
                if dashboard_manager.is_active():
                    dashboard_manager.state.consume_skip_task_request()
                unfollow_jobs.remove(plugin)
                print_limits = True
            else:
                if active_limits_reached and plugin != "upload-posts":
                    logger.warning(
                        f"Can't perform {plugin} job because a limit for active-jobs has been reached."
                    )
                    print_limits = None
                    remaining_jobs = jobs_list[jobs_list.index(plugin) :]
                    if unfollow_jobs or "upload-posts" in remaining_jobs:
                        continue
                    else:
                        logger.info(
                            "No other jobs can be done cause of limit reached. Ending session.",
                            extra={"color": f"{Fore.CYAN}"},
                        )
                        break

                logger.info(
                    f"Current active-job: {plugin}",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
                if dashboard_manager.is_active():
                    dashboard_manager.state.current_job = plugin
                    dashboard_manager.state.current_action = f"Running {plugin}..."
                    dashboard_manager.update_render()
                if configs.args.scrape_to_file is not None:
                    logger.warning(
                        "You're in scraping mode! That means you're only collection data without interacting!"
                    )
                configs.actions[plugin].run(
                    device, configs, storage, sessions, filters, plugin
                )
                watchdog.heartbeat(f"job:{plugin}_done", f"Completed {plugin}")
                if dashboard_manager.is_active():
                    dashboard_manager.state.consume_skip_task_request()
                print_limits = True

        # save the session in sessions.json
        session_state.finishTime = datetime.now()
        sessions.persist(directory=session_state.my_username)

        # print reports
        if telegram_reports_at_end:
            logger.info("Going back to your profile..")
            profile_view.click_on_avatar()
            if profile_view.getFollowingCount() is None:
                profile_view.click_on_avatar()
            account_view.refresh_account()
            (
                _,
                _,
                followers_now,
                following_now,
            ) = profile_view.getProfileInfo()

        if analytics_at_end:
            configs.actions["analytics"].run(
                device, configs, storage, sessions, "analytics"
            )

        # turn off bot
        close_instagram(device)
        if configs.args.screen_sleep:
            device.screen_off()
            logger.info("Screen turned off for sleeping time.")

        if configs.args.kill_atx_agent:
            kill_atx_agent(device)
        head_up_notifications(enabled=True)
        logger.info(
            "-------- FINISH: "
            + str(session_state.finishTime.strftime("%H:%M:%S - %Y/%m/%d"))
            + " --------",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        pre_post_script(pre=False, path=configs.args.post_script)

        if (
            not only_upload_requested
            and configs.args.repeat
            and can_repeat(len(sessions), total_sessions)
        ):
            if dashboard_manager.is_active():
                dashboard_manager.stop()
                disable_tui_logging()
            print_full_report(sessions, configs.args.scrape_to_file)
            inside_working_hours, time_left = SessionState.inside_working_hours(
                configs.args.working_hours, configs.args.time_delta_session
            )
            if inside_working_hours:
                time_left = (
                    get_value(configs.args.repeat, "Sleep for {} minutes.", 180) * 60
                )
                print_telegram_reports(
                    configs,
                    telegram_reports_at_end,
                    followers_now,
                    following_now,
                    time_left,
                )
                logger.info(
                    f'Next session will start at: {(datetime.now() + timedelta(seconds=time_left)).strftime("%H:%M:%S (%Y/%m/%d)")}.'
                )
                watchdog.pause()
                try:
                    sleep(time_left)
                except KeyboardInterrupt:
                    stop_bot(
                        device,
                        sessions,
                        session_state,
                        was_sleeping=True,
                    )
                finally:
                    watchdog.resume()
            else:
                print_telegram_reports(
                    configs,
                    telegram_reports_at_end,
                    followers_now,
                    following_now,
                    time_left.total_seconds(),
                )
                watchdog.pause()
                wait_for_next_session(
                    time_left,
                    session_state,
                    sessions,
                    device,
                )
                watchdog.resume()
        else:
            break

    if dashboard_manager.is_active():
        dashboard_manager.stop()
        disable_tui_logging()

    watchdog.stop()
    SessionState.set_active(None)

    print_telegram_reports(
        configs,
        telegram_reports_at_end,
        followers_now,
        following_now,
    )
    print_full_report(sessions, configs.args.scrape_to_file)
    ask_for_a_donation()

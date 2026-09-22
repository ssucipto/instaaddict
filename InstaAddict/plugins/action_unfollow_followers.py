import logging
from enum import Enum, unique

from colorama import Fore, Style

from InstaAddict.core.decorators import run_safely
from InstaAddict.core.device_facade import DeviceFacade, Timeout
from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.resources import ClassName
from InstaAddict.core.resources import ResourceID as resources
from InstaAddict.core.scroll_end_detector import ScrollEndDetector
from InstaAddict.core.storage import FollowingStatus
from InstaAddict.core.utils import (
    EmptyList,
    get_value,
    inspect_current_view,
    random_sleep,
    save_crash,
)
from InstaAddict.core.views import (
    Direction,
    FollowingView,
    ProfileView,
    UniversalActions,
)
from InstaAddict.plugins.telegram import load_telegram_config, telegram_bot_send_text

logger = logging.getLogger(__name__)

FOLLOWING_REGEX = "^Following|^Requested"
UNFOLLOW_REGEX = "^Unfollow"


class ActionUnfollowFollowers(Plugin):
    """Handles the functionality of unfollowing your followers"""

    def __init__(self):
        super().__init__()
        self.description = "Handles the functionality of unfollowing your followers"
        self.arguments = [
            {
                "arg": "--unfollow",
                "nargs": None,
                "help": "unfollow at most given number of users. Only users followed by this script will be unfollowed. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-non-followers",
                "nargs": None,
                "help": "unfollow at most given number of users, that don't follow you back. Only users followed by this script will be unfollowed. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-any-non-followers",
                "nargs": None,
                "help": "unfollow at most given number of users, that don't follow you back. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-any-followers",
                "nargs": None,
                "help": "unfollow at most given number of users, that follow you back. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-any",
                "nargs": None,
                "help": "unfollow at most given number of users. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--min-following",
                "nargs": None,
                "help": "minimum amount of followings, after reaching this amount unfollow stops",
                "metavar": "100",
                "default": 0,
            },
            {
                "arg": "--sort-followers-newest-to-oldest",
                "help": "sort the followers from newest to oldest instead of vice-versa (default)",
                "action": "store_true",
            },
            {
                "arg": "--unfollow-delay",
                "nargs": None,
                "help": "unfollow users followed by the bot after x amount of days",
                "metavar": "3",
                "default": "0",
            },
            {
                "arg": "--clear-non-bot-cache",
                "help": "clear the persistent cache of non-bot followings before starting",
                "action": "store_true",
            },
            {
                "arg": "--ignore-non-bot-cache",
                "help": "ignore the persistent non-bot followings cache during this session",
                "action": "store_true",
            },
            {
                "arg": "--sort-followings-by-latest",
                "help": "sort followings from newest to oldest (Latest) to target recently followed accounts (default)",
                "action": "store_true",
            },
            {
                "arg": "--sort-followings-by-earliest",
                "help": "sort followings from oldest to newest (Earliest)",
                "action": "store_true",
            },
            {
                "arg": "--clear-followers-cache",
                "help": "clear the persistent local followers cache before starting",
                "action": "store_true",
            },
            {
                "arg": "--ignore-followers-cache",
                "help": "ignore the persistent local followers cache during this session",
                "action": "store_true",
            },
        ]

    def run(self, device, configs, storage, sessions, profile_filter, plugin):
        class State:
            def __init__(self):
                pass

            unfollowed_count = 0
            is_job_completed = False

        self.args = configs.args
        self.device_id = configs.args.device
        self.state = State()
        self.no_unfollow_option = []
        self.session_state = sessions[-1]
        self.sessions = sessions
        self.unfollow_type = plugin
        self.ResourceID = resources(self.args.app_id)

        count_arg = get_value(
            getattr(self.args, self.unfollow_type.replace("-", "_")),
            "Unfollow count: {}",
            10,
        )

        count = min(
            count_arg,
            self.session_state.my_following_count - int(self.args.min_following),
        )
        if count < 1:
            logger.warning(
                f"Now you're following {self.session_state.my_following_count} accounts, {'less then' if count <0 else 'equal to'} min following allowed (you set min-following: {self.args.min_following}). No further unfollows are required. Finish."
            )
            return
        elif self.session_state.my_following_count < count_arg:
            logger.warning(
                f"You can't unfollow {count_arg} accounts, because you are following {self.session_state.my_following_count} accounts. For that reason only {count} unfollows can be performed."
            )
        elif count < count_arg:
            logger.warning(
                f"You can't unfollow {count_arg} accounts, because you set min-following to {self.args.min_following} and you have {self.session_state.my_following_count} followers. For that reason only {count} unfollows can be performed."
            )

        if self.unfollow_type == "unfollow":
            self.unfollow_type = UnfollowRestriction.FOLLOWED_BY_SCRIPT
        elif self.unfollow_type == "unfollow-non-followers":
            self.unfollow_type = UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS
        elif self.unfollow_type == "unfollow-any-non-followers":
            self.unfollow_type = UnfollowRestriction.ANY_NON_FOLLOWERS
        elif self.unfollow_type == "unfollow-any-followers":
            self.unfollow_type = UnfollowRestriction.ANY_FOLLOWERS
        else:
            self.unfollow_type = UnfollowRestriction.ANY

        @run_safely(
            device=device,
            device_id=self.device_id,
            sessions=self.sessions,
            session_state=self.session_state,
            screen_record=self.args.screen_record,
            configs=configs,
        )
        def job():
            self.unfollow(
                device,
                count - self.state.unfollowed_count,
                self.on_unfollow,
                storage,
                self.unfollow_type,
                self.session_state.my_username,
                plugin,
            )
            logger.info(
                f"Unfollowed {self.state.unfollowed_count}, finish.",
                extra={"color": f"{Fore.CYAN}"},
            )
            self.state.is_job_completed = True
            device.back()

        while not self.state.is_job_completed and (self.state.unfollowed_count < count):
            job()

        self._report_accounts_without_unfollow_option()

    def unfollow(
        self,
        device,
        count,
        on_unfollow,
        storage,
        unfollow_restriction,
        my_username,
        job_name,
    ):
        skipped_list_limit = get_value(self.args.skipped_list_limit, None, 15)
        skipped_fling_limit = get_value(self.args.fling_when_skipped, None, 0)
        posts_end_detector = ScrollEndDetector(
            repeats_to_end=2,
            skipped_list_limit=skipped_list_limit,
            skipped_fling_limit=skipped_fling_limit,
        )

        # Follower Count Delta Guard: Sync followers cache if evaluating non-followers
        if unfollow_restriction in [
            UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS,
            UnfollowRestriction.ANY_NON_FOLLOWERS,
            UnfollowRestriction.ANY_FOLLOWERS,
        ]:
            self._sync_followers_cache_if_needed(device, storage)

        ProfileView(device).navigateToFollowing()
        self.iterate_over_followings(
            device,
            count,
            on_unfollow,
            storage,
            unfollow_restriction,
            my_username,
            posts_end_detector,
            job_name,
        )

    def _sync_followers_cache_if_needed(self, device, storage):
        """
        Follower Count Delta Guard:
        Compares session_state.my_followers_count with storage.get_cached_followers_count().
        If delta == 0 and cache is populated, bypasses Followers list scraping entirely.
        If delta > 0 or cache is empty, fast-harvests recent followers to update cache.
        """
        clear_cache = getattr(self.args, "clear_followers_cache", False)
        ignore_cache = getattr(self.args, "ignore_followers_cache", False)

        if clear_cache and hasattr(storage, "clear_followers_cache"):
            logger.info("Clearing local followers cache as requested.")
            storage.clear_followers_cache()

        if ignore_cache or not hasattr(storage, "is_follower"):
            return

        current_count = getattr(self.session_state, "my_followers_count", None)
        cached_count = storage.get_cached_followers_count()
        cache_size = storage.get_followers_cache_size()

        needs_harvest = False
        if cache_size == 0:
            logger.info("Local followers cache is empty. Bootstrapping cache from Followers list...")
            needs_harvest = True
        elif current_count is not None and current_count > 0:
            delta = current_count - cached_count
            if delta > 0:
                logger.info(
                    f"Followers count increased by {delta} (from {cached_count} to {current_count}). "
                    f"Fast-harvesting recent followers to update cache..."
                )
                needs_harvest = True
            elif delta == 0:
                logger.info(
                    f"Followers count unchanged ({current_count}). "
                    f"Reusing local followers cache ({cache_size} known followers). Bypassing Followers list harvest!",
                    extra={"color": f"{Fore.GREEN}"},
                )
            else:
                logger.info(
                    f"Followers count decreased by {abs(delta)} ({cached_count} -> {current_count}). "
                    f"Updating cached count and using existing cache snapshot."
                )
                if hasattr(storage, "followers_cache"):
                    storage.followers_cache["last_followers_count"] = current_count
                    storage._followers_cache_dirty = True
                    storage.save_followers_cache()
        else:
            logger.debug(
                f"Current followers count unknown or zero. Using existing cache ({cache_size} entries)."
            )

        if needs_harvest:
            profile_view = ProfileView(device, is_own_profile=True)
            if profile_view.navigateToFollowers():
                max_scrolls = 2 if cache_size > 0 else 5
                new_followers = profile_view.harvest_visible_followers(max_scrolls=max_scrolls)
                if new_followers:
                    c_count = current_count if current_count and current_count > 0 else len(new_followers)
                    storage.add_followers_batch(
                        new_followers,
                        current_followers_count=c_count,
                        save=True,
                    )
                    logger.info(
                        f"Harvested {len(new_followers)} followers into local cache (total cached: {storage.get_followers_cache_size()}).",
                        extra={"color": f"{Fore.CYAN}"},
                    )
                device.back()
                random_sleep(1, 2)

    def on_unfollow(self):
        self.state.unfollowed_count += 1
        self.session_state.totalUnfollowed += 1

    def sort_followings_by_date(self, device, newest_to_oldest=None) -> bool:
        if newest_to_oldest is None:
            if getattr(self.args, "sort_followings_by_earliest", False):
                newest_to_oldest = False
            elif getattr(self.args, "sort_followers_newest_to_oldest", False) or getattr(
                self.args, "sort_followings_by_latest", False
            ):
                newest_to_oldest = True
            else:
                newest_to_oldest = True  # Modern optimized default: newest first

        sort_button = device.find(
            resourceId=self.ResourceID.SORTING_ENTRY_ROW_OPTION,
        )
        if not sort_button.exists(Timeout.MEDIUM):
            logger.error(
                "Cannot find button to sort followings. Continue without sorting."
            )
            return False
        sort_button.click()

        sort_options_recycler_view = device.find(
            resourceId=self.ResourceID.FOLLOW_LIST_SORTING_OPTIONS_RECYCLER_VIEW
        )
        if not sort_options_recycler_view.exists(Timeout.MEDIUM):
            logger.error(
                "Cannot find options to sort followings. Continue without sorting."
            )
            return False
        if newest_to_oldest:
            logger.info("Sort followings by date: from newest to oldest.")
            sort_options_recycler_view.child(textContains="Latest").click()
        else:
            logger.info("Sort followings by date: from oldest to newest.")
            sort_options_recycler_view.child(textContains="Earliest").click()
        return True

    def iterate_over_followings(
        self,
        device,
        count,
        on_unfollow,
        storage,
        unfollow_restriction,
        my_username,
        posts_end_detector,
        job_name,
    ):
        # Wait until list is rendered
        sorted = False
        for _ in range(2):
            user_lst = device.find(
                resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
                className=ClassName.LINEAR_LAYOUT,
            )
            user_lst.wait(Timeout.LONG)

            sort_container_obj = device.find(
                resourceId=self.ResourceID.SORTING_ENTRY_ROW_OPTION
            )
            if sort_container_obj.exists() and not sorted:
                newest_param = getattr(self.args, "sort_followers_newest_to_oldest", None)
                sorted = self.sort_followings_by_date(
                    device, newest_param
                )
                continue

            top_tab_obj = device.find(
                resourceId=self.ResourceID.UNIFIED_FOLLOW_LIST_TAB_LAYOUT
            )
            if sort_container_obj.exists(Timeout.SHORT) and top_tab_obj.exists(
                Timeout.SHORT
            ):
                sort_container_bounds = sort_container_obj.get_bounds()["top"]
                list_tab_bounds = top_tab_obj.get_bounds()["bottom"]
                delta = sort_container_bounds - list_tab_bounds
                UniversalActions(device)._swipe_points(
                    direction=Direction.DOWN,
                    start_point_y=sort_container_bounds,
                    delta_y=delta - 50,
                )
            else:
                UniversalActions(device)._swipe_points(
                    direction=Direction.DOWN, delta_y=380
                )

            if sort_container_obj.exists() and not sorted:
                newest_param = getattr(self.args, "sort_followers_newest_to_oldest", None)
                self.sort_followings_by_date(
                    device, newest_param
                )
                sorted = True
        clear_cache = getattr(self.args, "clear_non_bot_cache", False)
        ignore_cache = getattr(self.args, "ignore_non_bot_cache", False)

        if clear_cache and hasattr(storage, "clear_non_bot_followings"):
            logger.info("Clearing non-bot followings cache as requested.")
            storage.clear_non_bot_followings()

        checked = {}
        if (
            not ignore_cache
            and unfollow_restriction
            in [
                UnfollowRestriction.FOLLOWED_BY_SCRIPT,
                UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS,
            ]
            and hasattr(storage, "non_bot_followings")
        ):
            for cached_user in storage.non_bot_followings:
                checked[cached_user.casefold()] = None
            if storage.non_bot_followings:
                logger.info(
                    f"Loaded {len(storage.non_bot_followings)} known non-bot followings from cache."
                )

        unfollowed_count = 0
        total_unfollows_limit_reached = False
        posts_end_detector.notify_new_page()
        prev_screen_iterated_followings = []
        while True:
            try:
                from InstaAddict.core.tui import DashboardManager

                if DashboardManager.is_active():
                    dm = DashboardManager.get_instance()
                    if dm.state.is_skip_task_requested():
                        logger.warning(
                            "[TUI] Task skip requested by user ([CTRL+S]). Breaking out of unfollow early...",
                            extra={"color": f"{Fore.YELLOW}"},
                        )
                        break
                    if dm.state.is_upload_requested():
                        logger.info(
                            "[TUI] Immediate upload requested by user ([CTRL+U]). Exiting unfollow early to execute upload...",
                            extra={"color": f"{Fore.MAGENTA}"},
                        )
                        break
            except Exception:
                pass

            screen_iterated_followings = []
            logger.info("Iterate over visible followings.")
            try:
                from InstaAddict.core.watchdog import record_heartbeat

                record_heartbeat(
                    "unfollow-followers",
                    f"Iterating visible followings (checked: {len(checked)})",
                )
            except Exception:
                pass
            user_list = device.find(
                resourceIdMatches=self.ResourceID.USER_LIST_CONTAINER,
            )
            try:
                row_height, n_users = inspect_current_view(user_list)
            except EmptyList:
                logger.info(
                    "Followings list is empty or reached the end of list.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                break
            for item in user_list:
                try:
                    from InstaAddict.core.tui import DashboardManager
                    if DashboardManager.is_active() and DashboardManager.get_instance().state.is_skip_task_requested():
                        logger.warning(
                            "[TUI] Task skip requested by user ([CTRL+S]). Breaking out of unfollow items...",
                            extra={"color": f"{Fore.YELLOW}"},
                        )
                        break
                except Exception:
                    pass
                cur_row_height = item.get_height()
                if cur_row_height < row_height:
                    continue
                # Resilient username extraction from row item
                user_name_view = item.child(
                    resourceIdMatches=f"{self.ResourceID.ROW_USER_PRIMARY_NAME}|.*follow_list_username.*|.*row_profile_header_username.*"
                )
                if not user_name_view.exists():
                    user_info_view = item.child(index=1)
                    if user_info_view.exists():
                        candidate = user_info_view.child(index=0).child()
                        if candidate.exists():
                            user_name_view = candidate
                if not user_name_view.exists():
                    text_views = item.child(className=ClassName.TEXT_VIEW)
                    for tv in text_views:
                        txt = (tv.get_text() or "").strip()
                        if txt and not any(kw in txt.casefold() for kw in ["following", "follow", "remove", "message", "requested"]):
                            user_name_view = tv
                            break

                if not user_name_view.exists():
                    logger.info(
                        "Next item username not found: skipping item.",
                        extra={"color": f"{Fore.YELLOW}"},
                    )
                    continue

                try:
                    username = user_name_view.get_text()
                except Exception as e:
                    logger.debug(f"Transient error reading username view: {e}")
                    continue
                screen_iterated_followings.append(username)
                username_key = username.casefold() if username else ""
                if username_key not in checked:
                    checked[username_key] = None

                    if storage.is_user_in_whitelist(username):
                        logger.info(f"@{username} is in whitelist. Skip.")
                        continue

                    # Fast O(1) Follower Check for Non-Followers Unfollow Restrictions
                    if unfollow_restriction in [
                        UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS,
                        UnfollowRestriction.ANY_NON_FOLLOWERS,
                    ]:
                        if (
                            not getattr(self.args, "ignore_followers_cache", False)
                            and hasattr(storage, "is_follower")
                            and storage.is_follower(username)
                        ):
                            logger.info(
                                f"@{username} follows you (confirmed in local followers cache). Skip."
                            )
                            continue

                    if unfollow_restriction in [
                        UnfollowRestriction.FOLLOWED_BY_SCRIPT,
                        UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS,
                    ]:
                        if (
                            not ignore_cache
                            and hasattr(storage, "is_non_bot_following")
                            and storage.is_non_bot_following(username)
                        ):
                            logger.debug(
                                f"@{username} already recorded as not followed by this bot (cached). Skip."
                            )
                            continue

                        following_status = storage.get_following_status(username)
                        _, last_interaction = storage.check_user_was_interacted(
                            username
                        )
                        if following_status == FollowingStatus.NOT_IN_LIST:
                            logger.info(
                                f"@{username} has not been followed by this bot. Recorded to cache. Skip."
                            )
                            if hasattr(storage, "add_non_bot_following"):
                                storage.add_non_bot_following(username, save=False)
                            continue
                        elif not storage.can_be_unfollowed(
                            last_interaction,
                            get_value(self.args.unfollow_delay, None, 0),
                        ):
                            logger.info(
                                f"@{username} has been followed less then {self.args.unfollow_delay} days ago. Skip."
                            )
                            continue
                        elif following_status == FollowingStatus.UNFOLLOWED:
                            logger.info(
                                f"You have already unfollowed @{username} on {last_interaction}. Probably you got a soft ban at some point. Try again... Following status: {following_status.name}."
                            )
                        elif following_status not in (
                            FollowingStatus.FOLLOWED,
                            FollowingStatus.REQUESTED,
                        ):
                            logger.info(
                                f"Skip @{username}. Following status: {following_status.name}."
                            )
                            continue

                    if unfollow_restriction in [
                        UnfollowRestriction.ANY,
                        UnfollowRestriction.ANY_NON_FOLLOWERS,
                    ]:
                        following_status = storage.get_following_status(username)
                        if following_status == FollowingStatus.UNFOLLOWED:
                            logger.info(
                                f"Skip @{username}. Following status: {following_status.name}."
                            )
                            continue
                    if unfollow_restriction in [
                        UnfollowRestriction.ANY,
                        UnfollowRestriction.FOLLOWED_BY_SCRIPT,
                    ]:
                        unfollowed = FollowingView(device).do_unfollow_from_list(
                            user_row=item, username=username
                        )
                        if unfollowed is None:
                            self.no_unfollow_option.append(username)
                    else:
                        unfollowed = self.do_unfollow(
                            device,
                            username,
                            my_username,
                            unfollow_restriction
                            in [
                                UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS,
                                UnfollowRestriction.ANY_NON_FOLLOWERS,
                                UnfollowRestriction.ANY_FOLLOWERS,
                            ],
                            job_name == "unfollow-any-followers",
                            storage=storage,
                        )

                    if unfollowed:
                        storage.add_interacted_user(
                            username,
                            self.session_state.id,
                            unfollowed=True,
                            job_name=job_name,
                            target=None,
                        )
                        on_unfollow()
                        unfollowed_count += 1
                        total_unfollows_limit_reached = self.session_state.check_limit(
                            limit_type=self.session_state.Limit.UNFOLLOWS,
                            output=True,
                        )
                    if unfollowed_count >= count or total_unfollows_limit_reached:
                        if hasattr(storage, "save_non_bot_followings"):
                            storage.save_non_bot_followings()
                        return
                else:
                    logger.debug(f"Already checked {username} (or in non-bot cache).")

            if hasattr(storage, "save_non_bot_followings"):
                storage.save_non_bot_followings()

            if screen_iterated_followings != prev_screen_iterated_followings:
                prev_screen_iterated_followings = screen_iterated_followings
                logger.info("Need to scroll now.", extra={"color": f"{Fore.GREEN}"})
                list_view = device.find(
                    resourceId=self.ResourceID.LIST,
                )
                try:
                    if list_view.exists():
                        list_view.scroll(Direction.DOWN)
                    else:
                        device.swipe(Direction.UP)
                except Exception as e:
                    logger.debug(
                        f"List view scroll failed ({e}), falling back to gesture swipe."
                    )
                    device.swipe(Direction.UP)
                try:
                    from InstaAddict.core.watchdog import record_heartbeat

                    record_heartbeat(
                        "unfollow-followers",
                        f"Scrolled followings (checked: {len(checked)})",
                    )
                except Exception:
                    pass
            else:
                load_more_button = device.find(
                    resourceId=self.ResourceID.ROW_LOAD_MORE_BUTTON
                )
                if load_more_button.exists():
                    load_more_button.click()
                    random_sleep()
                    if load_more_button.exists():
                        logger.warning(
                            "Can't iterate over the list anymore, you may be soft-banned and cannot perform this action (refreshing follower list)."
                        )
                        if hasattr(storage, "save_non_bot_followings"):
                            storage.save_non_bot_followings()
                        return
                    list_view.scroll(Direction.DOWN)
                else:
                    logger.info(
                        "Reached the following list end, finish.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    if hasattr(storage, "save_non_bot_followings"):
                        storage.save_non_bot_followings()
                    return

    def do_unfollow(
        self,
        device: DeviceFacade,
        username,
        my_username,
        check_if_is_follower,
        unfollow_followers=False,
        storage=None,
    ):
        """
        :return: whether unfollow was successful
        """
        username_view = device.find(
            resourceId=self.ResourceID.FOLLOW_LIST_USERNAME,
            className=ClassName.TEXT_VIEW,
            text=username,
        )
        if not username_view.exists():
            logger.error(f"Cannot find @{username}, skip.")
            return False
        username_view.click_retry()

        is_following_you = self.check_is_follower(
            device, username, my_username, storage=storage
        )
        if is_following_you is not None:
            if check_if_is_follower and is_following_you:
                if not unfollow_followers:
                    logger.info(f"Skip @{username}. This user is following you.")
                    logger.info("Back to the followings list.")
                    device.back()
                    return False
                else:
                    logger.info(f"@{username} is following you, unfollow. 😈")
            unfollow_button = device.find(
                classNameMatches=ClassName.BUTTON_OR_TEXTVIEW_REGEX,
                textMatches=FOLLOWING_REGEX,
            )
            if not unfollow_button.exists():
                unfollow_button = device.find(
                    descriptionMatches=FOLLOWING_REGEX,
                )
            # I don't know/remember the origin of this, if someone does - let's document it
            attempts = 2
            for _ in range(attempts):
                if unfollow_button.exists():
                    break

                scrollable = device.find(classNameMatches=ClassName.VIEW_PAGER)
                if scrollable.exists():
                    scrollable.scroll(Direction.UP)
                unfollow_button = device.find(
                    classNameMatches=ClassName.BUTTON_OR_TEXTVIEW_REGEX,
                    textMatches=FOLLOWING_REGEX,
                )
                if not unfollow_button.exists():
                    unfollow_button = device.find(
                        descriptionMatches=FOLLOWING_REGEX,
                    )

            if not unfollow_button.exists():
                logger.error("Cannot find Following button.")
                save_crash(device)
            logger.debug("Unfollow button click.")
            unfollow_button.click()
            logger.info(f"Unfollow @{username}.", extra={"color": f"{Fore.YELLOW}"})

            # Weirdly enough, this is a fix for after you unfollow someone that follows
            # you back - the next person you unfollow the button is missing on first find
            # additional find - finds it. :shrug:
            confirm_unfollow_button = None
            attempts = 2
            for _ in range(attempts):
                confirm_unfollow_button = device.find(
                    resourceId=self.ResourceID.FOLLOW_SHEET_UNFOLLOW_ROW
                )
                if confirm_unfollow_button.exists(Timeout.SHORT):
                    break
                confirm_unfollow_button = device.find(
                    classNameMatches=ClassName.BUTTON_OR_TEXTVIEW_REGEX,
                    textMatches="(?i)^Unfollow$",
                )
                if confirm_unfollow_button.exists(Timeout.SHORT):
                    break
                confirm_unfollow_button = device.find(
                    descriptionMatches="(?i)^Unfollow$"
                )
                if confirm_unfollow_button.exists(Timeout.SHORT):
                    break

            if not confirm_unfollow_button or not confirm_unfollow_button.exists():
                logger.error("Cannot confirm unfollow.")
                save_crash(device)
                device.back()
                return False
            logger.debug("Confirm unfollow.")
            confirm_unfollow_button.click()

            random_sleep(0, 1, modulable=False)

            # Check if private account confirmation
            private_unfollow_button = device.find(
                classNameMatches=ClassName.BUTTON_OR_TEXTVIEW_REGEX,
                textMatches=UNFOLLOW_REGEX,
            )
            if private_unfollow_button.exists(Timeout.SHORT):
                logger.debug("Confirm unfollow private account.")
                private_unfollow_button.click()

            UniversalActions.detect_block(device)
        else:
            logger.info("Back to the followings list.")
            device.back()
            return False
        logger.info("Back to the followings list.")
        device.back()
        return True

    def _report_accounts_without_unfollow_option(self):
        """Send the list of accounts that have no Unfollow option to telegram.
        Never fails: if telegram is not configured or sending fails, just log."""
        if not self.no_unfollow_option:
            return
        logger.info(
            f"{len(self.no_unfollow_option)} account(s) have no Unfollow option: {', '.join('@' + u for u in self.no_unfollow_option)}."
        )
        try:
            username = self.args.username
            if username is None:
                logger.info("No username set - skipping telegram report.")
                return
            telegram_config = load_telegram_config(username)
            if not telegram_config:
                logger.info(
                    "Telegram is not configured - skipping report of accounts without Unfollow option."
                )
                return
            usernames_list = "\n".join(
                f"\u2022 @{u}" for u in self.no_unfollow_option
            )
            text = (
                f"*Accounts without the Unfollow option ({len(self.no_unfollow_option)}):*\n"
                f"{usernames_list}"
            )
            response = telegram_bot_send_text(
                telegram_config.get("telegram-api-token"),
                telegram_config.get("telegram-chat-id"),
                text,
            )
            if response and response.get("ok"):
                logger.info(
                    "Telegram message sent successfully.",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
            else:
                error = response.get("description") if response else "Unknown error"
                logger.error(f"Failed to send Telegram message: {error}")
        except Exception as e:
            logger.error(f"Can't report accounts without Unfollow option: {e}")

    def check_is_follower(self, device, username, my_username, storage=None):
        logger.info(
            f"Check if @{username} is following you.", extra={"color": f"{Fore.GREEN}"}
        )

        # Tier 1: Local cache check
        if (
            storage is not None
            and hasattr(storage, "is_follower")
            and storage.is_follower(username)
        ):
            logger.info(
                f"@{username} follows you (confirmed via local followers cache)."
            )
            return True

        # Tier 2: Profile header 'Follows you' badge or context label
        profile_view = ProfileView(device)
        if (
            hasattr(profile_view, "has_follows_you_badge")
            and profile_view.has_follows_you_badge()
        ):
            logger.info(
                f"@{username} has 'Follows you' badge on profile. Verified as follower."
            )
            if storage is not None and hasattr(storage, "add_follower"):
                storage.add_follower(username)
            return True

        # Tier 3: If on candidate profile and no 'Follows you' badge found, they do NOT follow you
        logger.info(
            f"@{username} does NOT follow you (no 'Follows you' badge found on profile)."
        )
        return False


@unique
class UnfollowRestriction(Enum):
    ANY = 0
    FOLLOWED_BY_SCRIPT = 1
    FOLLOWED_BY_SCRIPT_NON_FOLLOWERS = 2
    ANY_NON_FOLLOWERS = 3
    ANY_FOLLOWERS = 4

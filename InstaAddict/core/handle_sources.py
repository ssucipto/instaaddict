import logging
import os
from functools import partial
from os import path
from random import randint

from atomicwrites import atomic_write
from colorama import Fore

from InstaAddict.plugins.telegram import load_telegram_config, telegram_bot_send_photo

from InstaAddict.core.device_facade import DeviceFacade, Direction, Timeout
from InstaAddict.core.navigation import (
    nav_to_blogger,
    nav_to_feed,
    nav_to_hashtag_or_place,
    nav_to_post_likers,
)
from InstaAddict.core.resources import ClassName
from InstaAddict.core.storage import FollowingStatus
from InstaAddict.core.utils import (
    EmptyList,
    get_value,
    inspect_current_view,
    random_choice,
    random_sleep,
)
from InstaAddict.core.views import (
    FollowingView,
    LikeMode,
    OpenedPostView,
    Owner,
    PostsViewList,
    ProfileView,
    SwipeTo,
    TabBarView,
    UniversalActions,
    case_insensitive_re,
)

logger = logging.getLogger(__name__)


def _record_source_skip(session_state, reason: str):
    """Safely record a profile skip reason and increment checked/skipped profile counters."""
    try:
        from InstaAddict.core.session_state import SessionState

        ss = session_state or SessionState.get_active()
        if ss:
            if hasattr(ss, "record_skip_reason"):
                ss.record_skip_reason(reason)
            if hasattr(ss, "increment_profiles_checked"):
                ss.increment_profiles_checked()
            if hasattr(ss, "increment_profiles_skipped"):
                ss.increment_profiles_skipped()
    except Exception:
        pass


def interact(
    storage,
    is_follow_limit_reached,
    username,
    interaction,
    device,
    session_state,
    current_job,
    target,
    on_interaction,
):
    can_follow = False
    if is_follow_limit_reached is not None:
        can_follow = not is_follow_limit_reached() and storage.get_following_status(
            username
        ) in [FollowingStatus.NONE, FollowingStatus.NOT_IN_LIST]

    (
        interaction_succeed,
        followed,
        requested,
        scraped,
        pm_sent,
        number_of_liked,
        number_of_watched,
        number_of_comments,
    ) = interaction(device, username=username, can_follow=can_follow)

    add_interacted_user = partial(
        storage.add_interacted_user,
        session_id=session_state.id,
        job_name=current_job,
        target=target,
    )

    add_interacted_user(
        username,
        followed=followed,
        is_requested=requested,
        scraped=scraped,
        liked=number_of_liked,
        watched=number_of_watched,
        commented=number_of_comments,
        pm_sent=pm_sent,
    )
    return on_interaction(
        succeed=interaction_succeed,
        followed=followed,
        scraped=scraped,
    )


def handle_blogger(
    self,
    device,
    session_state,
    blogger,
    current_job,
    storage,
    profile_filter,
    on_interaction,
    interaction,
    is_follow_limit_reached,
):
    try:
        from InstaAddict.core.tui import DashboardManager

        if DashboardManager.is_active():
            dm = DashboardManager.get_instance()
            if dm.state.is_skip_task_requested():
                logger.warning(
                    f"[TUI] Task skip requested by user ([CTRL+S]). Skipping blogger @{blogger}...",
                    extra={"color": f"{Fore.YELLOW}"},
                )
                return
            if dm.state.is_upload_requested():
                logger.info(
                    f"[TUI] Immediate upload requested by user ([CTRL+U]). Exiting blogger @{blogger} to execute upload...",
                    extra={"color": f"{Fore.MAGENTA}"},
                )
                return
    except Exception:
        pass

    if not nav_to_blogger(device, blogger, session_state.my_username):
        return
    can_interact = False
    if storage.is_user_in_blacklist(blogger):
        logger.info(f"@{blogger} is in blacklist. Skip.")
        _record_source_skip(session_state, "BLACKLIST")
    else:
        interacted, interacted_when = storage.check_user_was_interacted(blogger)
        if interacted:
            can_reinteract = storage.can_be_reinteract(
                interacted_when, get_value(self.args.can_reinteract_after, None, 0)
            )
            logger.info(
                f"@{blogger}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
            )
            if can_reinteract:
                can_interact = True
            else:
                _record_source_skip(session_state, "COOLDOWN")
        else:
            can_interact = True

    if can_interact:
        logger.info(
            f"@{blogger}: interact",
            extra={"color": f"{Fore.YELLOW}"},
        )
        if not interact(
            storage=storage,
            is_follow_limit_reached=is_follow_limit_reached,
            username=blogger,
            interaction=interaction,
            device=device,
            session_state=session_state,
            current_job=current_job,
            target=blogger,
            on_interaction=on_interaction,
        ):
            return


def handle_blogger_from_file(
    self,
    device,
    parameter_passed,
    current_job,
    storage,
    on_interaction,
    interaction,
    is_follow_limit_reached,
):
    need_to_refresh = True
    on_following_list = False
    limit_reached = False

    filename: str = os.path.join(storage.account_path, parameter_passed.split(" ")[0])
    try:
        amount_of_users = get_value(parameter_passed.split(" ")[1], None, 10)
    except IndexError:
        amount_of_users = 10
        logger.warning(
            f"You didn't passed how many users should be processed from the list! Default is {amount_of_users} users."
        )
    if path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as f:
            usernames = [line.replace(" ", "") for line in f if line != "\n"]
        len_usernames = len(usernames)
        if len_usernames < amount_of_users:
            amount_of_users = len_usernames
        logger.info(
            f"In {filename} there are {len_usernames} entries, {amount_of_users} users will be processed."
        )
        not_found = []
        processed_users = 0
        try:
            for line, username_raw in enumerate(usernames, start=1):
                username = username_raw.strip()
                can_interact = False
                if current_job == "unfollow-from-file":
                    unfollowed = do_unfollow_from_list(
                        device, username, on_following_list
                    )
                    on_following_list = True
                    if unfollowed:
                        storage.add_interacted_user(
                            username, self.session_state.id, unfollowed=True
                        )
                        self.session_state.totalUnfollowed += 1
                        limit_reached = self.session_state.check_limit(
                            limit_type=self.session_state.Limit.UNFOLLOWS
                        )
                        processed_users += 1
                    else:
                        not_found.append(username_raw)
                    if limit_reached:
                        logger.info("Unfollows limit reached.")
                        break
                    if processed_users == amount_of_users:
                        logger.info(
                            f"{processed_users} users have been unfollowed, going to the next job."
                        )
                        break
                else:
                    if storage.is_user_in_blacklist(username):
                        logger.info(f"@{username} is in blacklist. Skip.")
                        _record_source_skip(session_state, "BLACKLIST")
                    else:
                        (
                            interacted,
                            interacted_when,
                        ) = storage.check_user_was_interacted(username)
                        if interacted:
                            can_reinteract = storage.can_be_reinteract(
                                interacted_when,
                                get_value(self.args.can_reinteract_after, None, 0),
                            )
                            logger.info(
                                f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                            )
                            if can_reinteract:
                                can_interact = True
                            else:
                                _record_source_skip(session_state, "COOLDOWN")
                        else:
                            can_interact = True

                    if not can_interact:
                        continue
                    if need_to_refresh:
                        search_view = TabBarView(device).navigateToSearch()
                    profile_view = search_view.navigate_to_target(username, current_job)
                    need_to_refresh = False
                    if not profile_view:
                        not_found.append(username_raw)
                        continue

                    if not interact(
                        storage=storage,
                        is_follow_limit_reached=is_follow_limit_reached,
                        username=username,
                        interaction=interaction,
                        device=device,
                        session_state=self.session_state,
                        current_job=current_job,
                        target=username,
                        on_interaction=on_interaction,
                    ):
                        return
                    device.back()
                    processed_users += 1
                    if processed_users == amount_of_users:
                        logger.info(
                            f"{processed_users} users have been interracted, going to the next job."
                        )
                        return
        finally:
            if not_found:
                with open(
                    f"{os.path.splitext(filename)[0]}_not_found.txt",
                    mode="a+",
                    encoding="utf-8",
                ) as f:
                    f.writelines(not_found)
            if self.args.delete_interacted_users and len_usernames != 0:
                with atomic_write(filename, overwrite=True, encoding="utf-8") as f:
                    f.writelines(usernames[line:])
    else:
        logger.warning(
            f"File {filename} not found. You have to specify the right relative path from this point: {os.getcwd()}"
        )
        return

    logger.info(f"Interact with users in {filename} completed.")
    device.back()


def do_unfollow_from_list(device, username, on_following_list):
    if not on_following_list:
        ProfileView(device).click_on_avatar()
        if ProfileView(device).navigateToFollowing() and UniversalActions(
            device
        ).search_text(username):
            return FollowingView(device).do_unfollow_from_list(username)
    else:
        if username is not None:
            UniversalActions(device).search_text(username)
        return FollowingView(device).do_unfollow_from_list(username)


def handle_likers(
    self,
    device,
    session_state,
    target,
    current_job,
    storage,
    profile_filter,
    posts_end_detector,
    on_interaction,
    interaction,
    is_follow_limit_reached,
):
    if (
        current_job == "blogger-post-likers"
        and not nav_to_post_likers(device, target, session_state.my_username)
        or current_job != "blogger-post-likers"
        and not nav_to_hashtag_or_place(device, target, current_job)
    ):
        return False
    post_description = ""
    nr_same_post = 0
    nr_same_posts_max = 3
    while True:
        if UniversalActions.escape_in_app_browser(device):
            logger.info(
                "Escaped in-app browser or advertisement overlay; swiping past."
            )
            UniversalActions(device)._swipe_points(
                direction=Direction.DOWN, delta_y=randint(450, 700)
            )
            random_sleep(inf=1, sup=3)
            continue

        (
            flag,
            post_description,
            username,
            is_ad,
            is_hashtag,
            has_tags,
        ) = PostsViewList(device)._check_if_last_post(
            post_description, current_job
        )
        if hasattr(session_state, "increment_posts_checked"):
            session_state.increment_posts_checked()
        try:
            from InstaAddict.core.tui import DashboardManager

            if DashboardManager.is_active():
                dm = DashboardManager.get_instance()
                act_str = f"Scanning post #{getattr(session_state, 'totalPostsChecked', 0)}"
                if username and username != "False":
                    act_str += f" (@{username})"
                dm.state.update_activity(
                    job=f"{current_job} ({target})" if target else str(current_job),
                    action=act_str,
                    target=username if username and username != "False" else None,
                    source=target or current_job,
                )
                dm.update_render()
        except Exception:
            pass

        try:
            from InstaAddict.core.watchdog import record_heartbeat

            record_heartbeat(
                stage=f"{current_job} ({target})" if target else str(current_job),
                action=f"Scanning post #{getattr(session_state, 'totalPostsChecked', 0)}",
            )
        except Exception:
            pass

        try:
            from InstaAddict.core.tui import DashboardManager

            if DashboardManager.is_active():
                dm = DashboardManager.get_instance()
                if dm.state.is_skip_task_requested():
                    logger.warning(
                        f"[TUI] Task skip requested by user ([CTRL+S]). Breaking out of likers for {target}...",
                        extra={"color": f"{Fore.YELLOW}"},
                    )
                    break
                if dm.state.is_upload_requested():
                    logger.info(
                        f"[TUI] Immediate upload requested by user ([CTRL+U]). Exiting {current_job} to execute upload...",
                        extra={"color": f"{Fore.MAGENTA}"},
                    )
                    break
        except Exception:
            pass

        if is_ad:
            if hasattr(session_state, "increment_ads_bypassed"):
                session_state.increment_ads_bypassed()
            logger.info(
                "Post is an advertisement, skipping in likers.",
                extra={"color": f"{Fore.CYAN}"},
            )
            PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
            continue

        has_likers, number_of_likers = PostsViewList(
            device
        )._find_likers_container()
        if flag:
            nr_same_post += 1
            logger.info(f"Warning: {nr_same_post}/{nr_same_posts_max} repeated posts.")
            if nr_same_post == nr_same_posts_max:
                logger.info(
                    f"Scrolled through {nr_same_posts_max} posts with same description and author. Finish.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                break
        else:
            nr_same_post = 0

        if (
            has_likers
            and profile_filter.is_num_likers_in_range(number_of_likers)
            and number_of_likers != 1
        ):
            PostsViewList(device).open_likers_container()
        else:
            PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
            continue

        posts_end_detector.notify_new_page()

        likes_list_view = OpenedPostView(device)._getListViewLikers()
        if likes_list_view is None:
            return
        prev_screen_iterated_likers = []

        while True:
            logger.info("Iterate over visible likers.")
            screen_iterated_likers = []
            opened = False
            user_container = OpenedPostView(device)._getUserContainer()
            if user_container is None:
                logger.warning("Likers list didn't load :(")
                return
            try:
                row_height, n_users = inspect_current_view(user_container)
            except EmptyList:
                logger.info("Likers list is empty or reached the end of list.")
                break
            try:
                for item in user_container:
                    cur_row_height = item.get_height()
                    if cur_row_height < row_height:
                        continue
                    element_opened = False
                    username_view = OpenedPostView(device)._getUserName(item)
                    if not username_view.exists(Timeout.MEDIUM):
                        logger.info(
                            "Next item not found: probably reached end of the screen.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        break

                    username = username_view.get_text()
                    screen_iterated_likers.append(username)
                    posts_end_detector.notify_username_iterated(username)
                    can_interact = False
                    if storage.is_user_in_blacklist(username):
                        logger.info(f"@{username} is in blacklist. Skip.")
                        _record_source_skip(session_state, "BLACKLIST")
                    else:
                        (
                            interacted,
                            interacted_when,
                        ) = storage.check_user_was_interacted(username)
                        if interacted:
                            can_reinteract = storage.can_be_reinteract(
                                interacted_when,
                                get_value(self.args.can_reinteract_after, None, 0),
                            )
                            logger.info(
                                f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                            )
                            if can_reinteract:
                                can_interact = True
                            else:
                                _record_source_skip(session_state, "COOLDOWN")
                        else:
                            can_interact = True

                    if can_interact:
                        logger.info(
                            f"@{username}: interact",
                            extra={"color": f"{Fore.YELLOW}"},
                        )
                        element_opened = username_view.click_retry()

                        if element_opened and not interact(
                            storage=storage,
                            is_follow_limit_reached=is_follow_limit_reached,
                            username=username,
                            interaction=interaction,
                            device=device,
                            session_state=session_state,
                            current_job=current_job,
                            target=target,
                            on_interaction=on_interaction,
                        ):
                            return
                    if element_opened:
                        opened = True
                        logger.info("Back to likers list.")
                        for _ in range(4):
                            if not ProfileView(device)._is_still_on_profile():
                                break
                            logger.debug("Still on profile, pressing back to return to likers list...")
                            device.back()
                            random_sleep(0.5, 1.0, modulable=False)

            except IndexError:
                logger.info(
                    "Cannot get next item: probably reached end of the screen.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                break
            go_back = False
            if screen_iterated_likers == prev_screen_iterated_likers:
                logger.info(
                    "Iterated exactly the same likers twice.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                go_back = True
            if go_back:
                prev_screen_iterated_likers.clear()
                prev_screen_iterated_likers += screen_iterated_likers
                logger.info(
                    f"Back to {target}'s posts list.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                device.back()
                logger.info("Going to the next post.")
                PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
                break
            if posts_end_detector.is_fling_limit_reached():
                logger.info(
                    "Reached fling limit. Fling to see other likers.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                likes_list_view.fling(Direction.DOWN)
            else:
                logger.info(
                    "Scroll to see other likers.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                likes_list_view.scroll(Direction.DOWN)

            prev_screen_iterated_likers.clear()
            prev_screen_iterated_likers += screen_iterated_likers
            if posts_end_detector.is_the_end():
                device.back()
                PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
                break
            if not opened:
                logger.info(
                    "All likers skipped.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                posts_end_detector.notify_skipped_all()
                if posts_end_detector.is_skipped_limit_reached():
                    posts_end_detector.reset_skipped_all()
                    return


def handle_posts(
    self,
    device,
    session_state,
    target,
    current_job,
    storage,
    profile_filter,
    on_interaction,
    interaction,
    is_follow_limit_reached,
    interact_percentage,
    scraping_file,
):
    skipped_posts_limit = get_value(
        self.args.skipped_posts_limit,
        "Skipped post limit: {}",
        5,
    )
    if current_job == "feed":
        if scraping_file:
            logger.warning(
                "Scraping and interacting with own feed doesn't make any sense. Skip."
            )
            return
        nav_to_feed(device)
        count_feed_limit = get_value(
            self.args.feed,
            "Feed interact count: {}",
            10,
        )
        count = 0
        PostsViewList(device)._refresh_feed()
    elif not nav_to_hashtag_or_place(device, target, current_job):
        if isinstance(current_job, str) and current_job.startswith("hashtag"):
            try:
                from InstaAddict.core.hashtag_manager import HashtagManager

                HashtagManager.get_instance(
                    username=getattr(session_state, "my_username", None)
                ).record_hashtag_result(target, posts_found=False)
            except Exception as e:
                logger.debug(f"HashtagManager record dead tag failed: {e}")
        return

    post_description = ""
    likes_failed = 0
    nr_same_post = 0
    nr_same_posts_max = 3
    nr_consecutive_already_interacted = 0
    nr_consecutive_unidentifiable = 0
    nr_consecutive_unidentifiable_max = 5
    already_liked_count = 0
    already_liked_count_limit = 20
    post_view_list = PostsViewList(device)
    opened_post_view = OpenedPostView(device)
    while True:
        try:
            from InstaAddict.core.tui import DashboardManager

            if DashboardManager.is_active():
                dm = DashboardManager.get_instance()
                if dm.state.is_skip_task_requested():
                    logger.warning(
                        f"[TUI] Task skip requested by user ([CTRL+S]). Breaking out of {current_job} ({target})...",
                        extra={"color": f"{Fore.YELLOW}"},
                    )
                    break
                if dm.state.is_upload_requested():
                    logger.info(
                        f"[TUI] Immediate upload requested by user ([CTRL+U]). Exiting {current_job} ({target}) to execute upload...",
                        extra={"color": f"{Fore.MAGENTA}"},
                    )
                    break
        except Exception:
            pass

        if UniversalActions.escape_in_app_browser(device):
            logger.info(
                "Escaped in-app browser or advertisement overlay; swiping past."
            )
            UniversalActions(device)._swipe_points(
                direction=Direction.DOWN, delta_y=randint(450, 700)
            )
            random_sleep(inf=1, sup=3)
            continue

        if UniversalActions.dismiss_peek_if_open(device):
            logger.info(
                "Escaped lingering Peek Preview popup overlay in feed; swiping past."
            )
            UniversalActions(device)._swipe_points(
                direction=Direction.DOWN, delta_y=randint(450, 700)
            )
            random_sleep(inf=1, sup=3)
            continue

        is_hashtag_job = (
            isinstance(current_job, str) and current_job.startswith("hashtag")
        )
        is_place_job = (
            isinstance(current_job, str) and current_job.startswith("place")
        )

        if (is_hashtag_job or is_place_job) and not opened_post_view.is_post_opened():
            logger.warning(
                f"Detected exit from post detail view back to grid in {current_job} ({target}). Exiting loop to prevent grid trap.",
                extra={"color": f"{Fore.YELLOW}"},
            )
            UniversalActions.check_micro_stall(
                device, context=f"grid_trap_exit_{current_job}"
            )
            break
        (
            is_same_post,
            post_description,
            username,
            is_ad,
            is_hashtag,
            has_tags,
        ) = post_view_list._check_if_last_post(post_description, current_job)
        if hasattr(session_state, "increment_posts_checked"):
            session_state.increment_posts_checked()
        try:
            from InstaAddict.core.tui import DashboardManager

            if DashboardManager.is_active():
                dm = DashboardManager.get_instance()
                act_str = f"Scanning post #{getattr(session_state, 'totalPostsChecked', 0)}"
                if username and username != "False":
                    act_str += f" (@{username})"
                dm.state.update_activity(
                    job=f"{current_job} ({target})" if target else str(current_job),
                    action=act_str,
                    target=username if username and username != "False" else None,
                    source=target or current_job,
                )
                dm.update_render()
        except Exception:
            pass

        try:
            from InstaAddict.core.watchdog import record_heartbeat

            if username and username != "False" and len(username.strip()) > 0:
                record_heartbeat(
                    stage=f"{current_job} ({target})" if target else str(current_job),
                    action=f"Scanning post #{getattr(session_state, 'totalPostsChecked', 0)} (@{username})",
                )
        except Exception:
            pass

        has_likers, number_of_likers = post_view_list._find_likers_container()
        already_liked, _ = opened_post_view._is_post_liked()

        is_hashtag_job = isinstance(current_job, str) and current_job.startswith("hashtag")
        no_harvest = (
            getattr(self.args, "no_harvest_hashtags", False)
            if hasattr(self, "args")
            else False
        )
        if is_hashtag_job and post_description and not is_ad and not no_harvest:
            try:
                from InstaAddict.core.hashtag_manager import HashtagManager

                HashtagManager.get_instance(
                    username=getattr(session_state, "my_username", None)
                ).harvest_from_caption(post_description, source_tag=target)
            except Exception as e:
                logger.debug(f"HashtagManager harvest failed: {e}")

        if is_ad:
            if hasattr(session_state, "increment_ads_bypassed"):
                session_state.increment_ads_bypassed()
            logger.info(
                "Post is an advertisement, skip.", extra={"color": f"{Fore.CYAN}"}
            )
            post_view_list.swipe_to_fit_posts(SwipeTo.NEXT_POST)
            continue
        if not (is_ad or is_hashtag):
            if not username or username == "False" or len(username.strip()) == 0:
                nr_consecutive_unidentifiable += 1
                logger.info(
                    f"No valid username found for post (unidentifiable author or ad) [{nr_consecutive_unidentifiable}/{nr_consecutive_unidentifiable_max}]. Skip.",
                    extra={"color": f"{Fore.YELLOW}"},
                )
                _record_source_skip(session_state, "UNIDENTIFIABLE")

                if nr_consecutive_unidentifiable >= nr_consecutive_unidentifiable_max:
                    logger.warning(
                        f"Exceeded max consecutive unidentifiable posts ({nr_consecutive_unidentifiable_max}) in {current_job} ({target}). "
                        f"Zero-net displacement or UI grid trap detected. Breaking out of source...",
                        extra={"color": f"{Fore.RED}"},
                    )
                    if is_hashtag_job:
                        try:
                            from InstaAddict.core.hashtag_manager import HashtagManager

                            HashtagManager.get_instance(
                                username=getattr(session_state, "my_username", None)
                            ).record_hashtag_result(target, posts_found=False)
                        except Exception as e:
                            logger.debug(
                                f"HashtagManager record unidentifiable trap failed: {e}"
                            )
                    UniversalActions.check_micro_stall(
                        device, context=f"consecutive_unidentifiable_{current_job}"
                    )
                    break

                UniversalActions.dismiss_peek_if_open(device)
                post_view_list.swipe_to_fit_posts(SwipeTo.NEXT_POST)
                continue

            nr_consecutive_unidentifiable = 0
            UniversalActions.get_micro_stall_sentinel().record_progress()
            if already_liked_count == already_liked_count_limit:
                logger.info(
                    f"Limit of {already_liked_count_limit} already liked posts limit reached, finish."
                )
                if is_hashtag_job:
                    try:
                        from InstaAddict.core.hashtag_manager import HashtagManager

                        HashtagManager.get_instance(
                            username=getattr(session_state, "my_username", None)
                        ).record_hashtag_result(
                            target, posts_found=True, already_liked_exhausted=True
                        )
                    except Exception as e:
                        logger.debug(f"HashtagManager record saturation failed: {e}")
                break
            if is_same_post:
                nr_same_post += 1
                logger.info(
                    f"Warning: {nr_same_post}/{nr_same_posts_max} repeated posts."
                )
                if nr_same_post == nr_same_posts_max:
                    logger.info(
                        f"Scrolled through {nr_same_posts_max} posts with same description and author. Finish."
                    )
                    break
            else:
                nr_same_post = 0
            if already_liked:
                logger.info(
                    "Post already liked, SKIP.", extra={"color": f"{Fore.CYAN}"}
                )
                already_liked_count += 1
            elif random_choice(interact_percentage):
                can_interact = False
                if storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip.")
                    _record_source_skip(session_state, "BLACKLIST")
                else:
                    likes_in_range = profile_filter.is_num_likers_in_range(
                        number_of_likers
                    )
                    if current_job != "feed":
                        interacted, interacted_when = storage.check_user_was_interacted(
                            username
                        )
                        if interacted:
                            can_reinteract = storage.can_be_reinteract(
                                interacted_when,
                                get_value(self.args.can_reinteract_after, None, 0),
                            )
                            logger.info(
                                f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                            )
                            if can_reinteract:
                                can_interact = True
                                nr_consecutive_already_interacted = 0
                            else:
                                nr_consecutive_already_interacted += 1
                                _record_source_skip(session_state, "COOLDOWN")
                        else:
                            can_interact = True
                            nr_consecutive_already_interacted = 0
                    else:
                        can_interact = True

                if nr_consecutive_already_interacted == skipped_posts_limit:
                    logger.info(
                        f"Reached the limit of already interacted {skipped_posts_limit}. Going to the next source/job!"
                    )
                    break
                try:
                    from InstaAddict.core.tui import DashboardManager
                    if DashboardManager.is_active() and DashboardManager.get_instance().state.is_skip_task_requested():
                        logger.warning(
                            f"[TUI] Task skip requested by user ([CTRL+S]). Breaking out of {current_job} ({target})...",
                            extra={"color": f"{Fore.YELLOW}"},
                        )
                        break
                except Exception:
                    pass
                if can_interact and (likes_in_range or not has_likers):
                    logger.info(
                        f"@{username}: interact", extra={"color": f"{Fore.YELLOW}"}
                    )
                    if scraping_file is None:
                        opened_post_view.start_video()
                        if not session_state.check_limit(
                            limit_type=session_state.Limit.LIKES, output=True
                        ):
                            if has_tags:
                                post_view_list._like_in_post_view(LikeMode.SINGLE_CLICK)
                            else:
                                post_view_list._like_in_post_view(LikeMode.DOUBLE_CLICK)
                            UniversalActions.detect_block(device)
                            liked = post_view_list._check_if_liked()
                            if not liked:
                                post_view_list._like_in_post_view(
                                    LikeMode.SINGLE_CLICK, already_watched=True
                                )
                                UniversalActions.detect_block(device)
                                liked = post_view_list._check_if_liked()
                            if liked:
                                session_state.totalLikes += 1
                                if is_hashtag_job:
                                    try:
                                        from InstaAddict.core.hashtag_manager import HashtagManager

                                        HashtagManager.get_instance(
                                            username=getattr(session_state, "my_username", None)
                                        ).record_hashtag_result(
                                            target, posts_found=True, already_liked_exhausted=False
                                        )
                                    except Exception as e:
                                        logger.debug(f"HashtagManager reset saturation failed: {e}")

                                # Post-view commenting on feed or hashtag posts
                                raw_comment = getattr(getattr(self, "args", None), "comment_percentage", None)
                                comment_pct = (
                                    get_value(str(raw_comment), None, 0)
                                    if isinstance(raw_comment, (int, float, str))
                                    else 0
                                )
                                can_comment_job = True
                                if profile_filter is not None and hasattr(profile_filter, "can_comment"):
                                    try:
                                        _, _, _, can_comment_job = profile_filter.can_comment(current_job)
                                    except Exception:
                                        can_comment_job = True

                                comment_limit_reached = (
                                    session_state.check_limit(
                                        limit_type=session_state.Limit.COMMENTS, output=False
                                    ) is True
                                    if session_state and hasattr(session_state, "check_limit")
                                    else False
                                )
                                if can_comment_job and comment_pct > 0 and not comment_limit_reached:
                                    if randint(1, 100) <= comment_pct:
                                        try:
                                            from InstaAddict.core.interaction import _comment
                                            from InstaAddict.core.views import MediaType

                                            media_type = (
                                                opened_post_view.detect_opened_media_type()
                                                if hasattr(opened_post_view, "detect_opened_media_type")
                                                else MediaType.PHOTO
                                            )
                                            my_user = getattr(session_state, "my_username", None) or "FEED_INTERACTOR"
                                            commented = _comment(
                                                device,
                                                my_username=my_user,
                                                comment_percentage=100,
                                                args=getattr(self, "args", None),
                                                session_state=session_state,
                                                media_type=media_type,
                                            )
                                            if commented:
                                                logger.info(
                                                    "Successfully commented on post! 💬",
                                                    extra={"color": f"{Fore.GREEN}"},
                                                )
                                        except Exception as e:
                                            logger.error(f"Post-view comment error: {e}")

                                if current_job == "feed":
                                    count += 1
                                    if hasattr(session_state, "add_interaction"):
                                        session_state.add_interaction(
                                            "feed", succeed=True, followed=False, scraped=False
                                        )
                                    if storage is not None and hasattr(storage, "add_interacted_user"):
                                        try:
                                            storage.add_interacted_user(
                                                username,
                                                session_id=session_state.id if session_state else None,
                                                job_name=current_job,
                                                target=target,
                                                liked=1 if liked else 0,
                                                commented=1 if 'commented' in locals() and commented else 0,
                                                followed=False,
                                                is_requested=False,
                                                scraped=False,
                                                pm_sent=False,
                                            )
                                        except Exception as e:
                                            logger.debug(f"Storage add_interacted_user for feed: {e}")
                                    logger.info(
                                        f"Interacted feed bloggers: {count}/{count_feed_limit}"
                                    )
                                    likes_limit = self.session_state.check_limit(
                                        limit_type=self.session_state.Limit.LIKES
                                    )
                                    comments_limit = self.session_state.check_limit(
                                        limit_type=self.session_state.Limit.COMMENTS
                                    )
                                    success_limit = self.session_state.check_limit(
                                        limit_type=self.session_state.Limit.SUCCESS
                                    )
                                    total_limit = self.session_state.check_limit(
                                        limit_type=self.session_state.Limit.TOTAL
                                    )
                                    if likes_limit or comments_limit or success_limit or total_limit:
                                        logger.info("Limit reached, finish.")
                                        break
                                    if count >= count_feed_limit:
                                        logger.info(
                                            f"Interacted {count} bloggers in feed, finish."
                                        )
                                        break
                            else:
                                likes_failed += 1
                    if current_job != "feed":
                        opened, _, _ = post_view_list._post_owner(
                            current_job, Owner.OPEN, username
                        )
                        if opened:
                            if not interact(
                                storage=storage,
                                is_follow_limit_reached=is_follow_limit_reached,
                                username=username,
                                interaction=interaction,
                                device=device,
                                session_state=session_state,
                                current_job=current_job,
                                target=target,
                                on_interaction=on_interaction,
                            ):
                                break
                            if is_hashtag_job:
                                try:
                                    from InstaAddict.core.hashtag_manager import HashtagManager

                                    HashtagManager.get_instance(
                                        username=getattr(session_state, "my_username", None)
                                    ).record_hashtag_result(
                                        target, posts_found=True, already_liked_exhausted=False
                                    )
                                except Exception as e:
                                    logger.debug(f"HashtagManager reset saturation failed: {e}")
                            for _ in range(4):
                                if not ProfileView(device)._is_still_on_profile():
                                    break
                                logger.debug("Still on blogger's profile, pressing back to return to source list...")
                                device.back()
                                random_sleep(0.5, 1.0, modulable=False)

            else:
                logger.info(
                    f"Skipped because your interact % is {interact_percentage}/100 and {username}'s post was unlucky!"
                )
        if likes_failed == 10:
            logger.warning("You failed to do 10 likes! Soft-ban?!")
            return
        post_view_list.swipe_to_fit_posts(SwipeTo.NEXT_POST)
    TabBarView(device).navigateToProfile()


def handle_followers(
    self,
    device,
    session_state,
    username,
    current_job,
    storage,
    on_interaction,
    interaction,
    is_follow_limit_reached,
    scroll_end_detector,
):
    is_myself = username == session_state.my_username
    if not nav_to_blogger(device, username, current_job):
        return

    iterate_over_followers(
        self,
        device,
        interaction,
        is_follow_limit_reached,
        storage,
        on_interaction,
        is_myself,
        scroll_end_detector,
        session_state,
        current_job,
        username,
    )


def check_and_report_restricted_list(device, session_state, target_username):
    no_results_heading = device.find(
        className=ClassName.TEXT_VIEW,
        textMatches=case_insensitive_re("No results"),
    )
    restricted_text = device.find(
        className=ClassName.TEXT_VIEW,
        textMatches=case_insensitive_re(".*We limit certain things.*"),
    )
    if not no_results_heading.exists() and not restricted_text.exists():
        return False

    logger.warning(
        f"@{target_username}'s followers/following list is restricted by Instagram.",
        extra={"color": f"{Fore.RED}"},
    )

    try:
        my_username = session_state.my_username
        telegram_config = load_telegram_config(my_username)
        if not telegram_config:
            logger.debug(
                f"No telegram configuration found for {my_username}. Skipping restriction alert."
            )
            return True

        os.makedirs("crashes", exist_ok=True)
        screenshot_path = os.path.join("crashes", "restricted_list.png")
        device.screenshot(screenshot_path)

        telegram_bot_send_photo(
            telegram_config.get("telegram-api-token"),
            telegram_config.get("telegram-chat-id"),
            screenshot_path,
            caption=f"⚠️ Followers/following list restricted for @{target_username}",
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram restriction alert: {e}")

    return True


def iterate_over_followers(
    self,
    device,
    interaction,
    is_follow_limit_reached,
    storage,
    on_interaction,
    is_myself,
    scroll_end_detector,
    session_state,
    current_job,
    target,
):
    device.find(
        resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
        className=ClassName.LINEAR_LAYOUT,
    ).wait(Timeout.LONG)

    def scrolled_to_top():
        row_search = device.find(
            resourceId=self.ResourceID.ROW_SEARCH_EDIT_TEXT,
            className=ClassName.EDIT_TEXT,
        )
        return row_search.exists()

    while True:
        try:
            from InstaAddict.core.tui import DashboardManager
            if DashboardManager.is_active():
                dm = DashboardManager.get_instance()
                if dm.state.is_skip_task_requested():
                    logger.warning(
                        f"[TUI] Task skip requested by user ([CTRL+S]). Breaking out of followers for @{target}...",
                        extra={"color": f"{Fore.YELLOW}"},
                    )
                    break
        except Exception:
            pass
        logger.info("Iterate over visible followers.")
        try:
            from InstaAddict.core.watchdog import record_heartbeat

            record_heartbeat(
                "blogger-followers", f"Iterating followers for @{target}"
            )
        except Exception:
            pass
        screen_iterated_followers = []
        screen_skipped_followers_count = 0
        scroll_end_detector.notify_new_page()
        user_list = device.find(
            resourceIdMatches=self.ResourceID.USER_LIST_CONTAINER,
        )
        try:
            row_height, n_users = inspect_current_view(user_list)
        except EmptyList:
            if check_and_report_restricted_list(device, session_state, target):
                logger.warning(
                    f"Instagram restricted the list for @{target}. Skipping this account.",
                    extra={"color": f"{Fore.RED}"},
                )
                logger.info("Back to blogger profile")
                device.back()
                random_sleep(1, 2, modulable=False)
                device.back()
                device.back()
                return
            logger.warning(
                f"Followers list for @{target} is empty, restricted, or un-rendered. Skipping this account.",
                extra={"color": f"{Fore.YELLOW}"},
            )
            logger.info("Back to blogger profile")
            device.back()
            random_sleep(1, 2, modulable=False)
            device.back()
            device.back()
            return
        try:
            for item in user_list:
                try:
                    from InstaAddict.core.tui import DashboardManager
                    if DashboardManager.is_active() and DashboardManager.get_instance().state.is_skip_task_requested():
                        logger.warning(
                            f"[TUI] Task skip requested by user ([CTRL+S]). Breaking out of followers list for @{target}...",
                            extra={"color": f"{Fore.YELLOW}"},
                        )
                        break
                except Exception:
                    pass
                try:
                    cur_row_height = item.get_height()
                except DeviceFacade.JsonRpcError:
                    logger.info(
                        "Item no longer visible: reached end of the screen.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    break
                if cur_row_height < row_height:
                    continue
                user_info_view = item.child(index=1)
                user_name_view = user_info_view.child(index=0).child()
                if not user_name_view.exists():
                    logger.info(
                        "Next item not found: probably reached end of the screen.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    break

                username = user_name_view.get_text()
                screen_iterated_followers.append(username)
                scroll_end_detector.notify_username_iterated(username)

                can_interact = False
                if storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip.")
                    _record_source_skip(session_state, "BLACKLIST")
                else:
                    interacted, interacted_when = storage.check_user_was_interacted(
                        username
                    )
                    if interacted:
                        can_reinteract = storage.can_be_reinteract(
                            interacted_when,
                            get_value(self.args.can_reinteract_after, None, 0),
                        )
                        logger.info(
                            f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                        )
                        if can_reinteract:
                            can_interact = True
                        else:
                            screen_skipped_followers_count += 1
                            _record_source_skip(session_state, "COOLDOWN")
                    else:
                        can_interact = True

                if can_interact:
                    logger.info(
                        f"@{username}: interact", extra={"color": f"{Fore.YELLOW}"}
                    )
                    element_opened = user_name_view.click_retry()

                    if element_opened:
                        if not interact(
                            storage=storage,
                            is_follow_limit_reached=is_follow_limit_reached,
                            username=username,
                            interaction=interaction,
                            device=device,
                            session_state=session_state,
                            current_job=current_job,
                            target=target,
                            on_interaction=on_interaction,
                        ):
                            return
                    if element_opened:
                        logger.info("Back to followers list")
                        device.back()

        except IndexError:
            logger.info(
                "Cannot get next item: probably reached end of the screen.",
                extra={"color": f"{Fore.GREEN}"},
            )

        if is_myself and scrolled_to_top():
            logger.info("Scrolled to top, finish.", extra={"color": f"{Fore.GREEN}"})
            # Navigate back to SEARCH after finishing followers iteration
            # First back goes to blogger's profile, second back goes to SEARCH
            logger.info("Navigating back to SEARCH")
            device.back()
            device.back()
            # Check if we landed on active search-input screen (no tab bar)
            # If so, press back again to dismiss it
            search_input = device.find(
                resourceId=self.ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT
            )
            if search_input.exists():
                logger.debug("On active search-input screen, pressing back to dismiss")
                device.back()
            return
        elif len(screen_iterated_followers) > 0:
            load_more_button = device.find(
                resourceId=self.ResourceID.ROW_LOAD_MORE_BUTTON
            )
            load_more_button_exists = load_more_button.exists()

            see_more_button = device.find(
                resourceId=self.ResourceID.SEE_ALL_BUTTON,
            )
            if not see_more_button.exists():
                see_more_button = device.find(
                    className=ClassName.TEXT_VIEW,
                    textMatches=case_insensitive_re("See more"),
                )
            if see_more_button.exists():
                logger.info(
                    'Found "See more" button, loading more followers.',
                    extra={"color": f"{Fore.GREEN}"},
                )
                see_more_button.click_retry()
                random_sleep(2, 4, modulable=False)
                continue

            if scroll_end_detector.is_the_end():
                # Navigate back to SEARCH after finishing followers iteration
                # First back goes to blogger's profile, second back goes to SEARCH
                logger.info("End of followers list, navigating back to SEARCH")
                device.back()
                device.back()
                # Check if we landed on active search-input screen (no tab bar)
                # If so, press back again to dismiss it
                search_input = device.find(
                    resourceId=self.ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT
                )
                if search_input.exists():
                    logger.debug(
                        "On active search-input screen, pressing back to dismiss"
                    )
                    device.back()
                return

            need_swipe = screen_skipped_followers_count == len(
                screen_iterated_followers
            )
            list_view = device.find(
                resourceId=self.ResourceID.LIST, className=ClassName.LIST_VIEW
            )
            if not list_view.exists():
                logger.error(
                    "Cannot find the list of followers. Trying to press back again."
                )
                device.back()
                list_view = device.find(
                    resourceId=self.ResourceID.LIST,
                    className=ClassName.LIST_VIEW,
                )

            def _scroll_or_swipe(down: bool = True, fling_mode: bool = False):
                try:
                    if list_view.exists():
                        direction = Direction.DOWN if down else Direction.UP
                        if fling_mode and hasattr(list_view, "fling"):
                            list_view.fling(direction)
                            return
                        list_view.scroll(direction)
                        return
                except Exception as ex:
                    logger.debug(
                        f"list_view scroll failed ({ex}), using gesture swipe."
                    )
                swipe_dir = Direction.UP if down else Direction.DOWN
                device.swipe(swipe_dir)

            if is_myself:
                logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                _scroll_or_swipe(down=False)
            else:
                pressed_retry = False
                if load_more_button_exists:
                    retry_button = load_more_button.child(
                        className=ClassName.IMAGE_VIEW,
                        descriptionMatches=case_insensitive_re("Retry"),
                    )
                    if retry_button.exists():
                        random_sleep()
                        """It exist but can disappear without pressing on it"""
                        if retry_button.exists():
                            logger.info('Press "Load" button and wait few seconds.')
                            retry_button.click_retry()
                            random_sleep(5, 10, modulable=False)
                            pressed_retry = True

                if need_swipe and not pressed_retry:
                    scroll_end_detector.notify_skipped_all()
                    if scroll_end_detector.is_skipped_limit_reached():
                        return
                    if scroll_end_detector.is_fling_limit_reached():
                        logger.info(
                            "Limit of all followers skipped reached, let's fling.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        _scroll_or_swipe(down=True, fling_mode=True)
                    else:
                        logger.info(
                            "All followers skipped, let's scroll.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        _scroll_or_swipe(down=True)
                else:
                    logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                    _scroll_or_swipe(down=True)

            try:
                from InstaAddict.core.watchdog import record_heartbeat

                record_heartbeat(
                    "blogger-followers", f"Scrolled followers list for @{target}"
                )
            except Exception:
                pass
        else:
            logger.info(
                "No followers were iterated, finish.",
                extra={"color": f"{Fore.GREEN}"},
            )
            return

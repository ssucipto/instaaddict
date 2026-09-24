import logging
import sys

from colorama import Fore

from InstaAddict.core.device_facade import Timeout
from InstaAddict.core.utils import random_sleep
from InstaAddict.core.views import (
    HashTagView,
    OpenedPostView,
    PlacesView,
    PostsGridView,
    ProfileView,
    TabBarView,
    UniversalActions,
)

logger = logging.getLogger(__name__)


def check_if_english(device):
    """check if app is in English"""
    logger.debug("Checking if app is in English..")
    post, follower, following = ProfileView(device)._getSomeText()
    if None in {post, follower, following}:
        logger.warning(
            "Failed to check your Instagram language. Be sure to set it to English or the bot won't work!"
        )
    elif post == "posts" and follower == "followers" and following == "following":
        logger.debug("Instagram in English.")
    else:
        logger.error("Please change the language manually to English!")
        sys.exit(1)
    return ProfileView(device, is_own_profile=True)


def nav_to_blogger(device, username, current_job):
    """navigate to blogger (followers list or posts)"""
    _to_followers = bool(current_job.endswith("followers"))
    _to_following = bool(current_job.endswith("following"))
    if username is None:
        profile_view = TabBarView(device).navigateToProfile()
        if _to_followers:
            logger.info("Open your followers.")
            profile_view.navigateToFollowers()
        elif _to_following:
            logger.info("Open your following.")
            profile_view.navigateToFollowing()
    else:
        search_view = TabBarView(device).navigateToSearch()
        if not search_view.navigate_to_target(username, current_job):
            return False

        profile_view = ProfileView(device, is_own_profile=False)
        if _to_followers:
            logger.info(f"Open @{username} followers.")
            profile_view.navigateToFollowers()
        elif _to_following:
            logger.info(f"Open @{username} following.")
            profile_view.navigateToFollowing()

    return True


def nav_to_hashtag_or_place(device, target, current_job):
    """navigate to hashtag/place/feed list"""
    search_view = TabBarView(device).navigateToSearch()
    if not search_view.navigate_to_target(target, current_job):
        return False

    TargetView = HashTagView if current_job.startswith("hashtag") else PlacesView

    if current_job.endswith("recent"):
        logger.info("Switching to Recent tab.")
        recent_tab = TargetView(device)._getRecentTab()
        if recent_tab.exists(Timeout.MEDIUM):
            recent_tab.click()
        else:
            logger.info("Recent tab not found (Instagram modern layout defaults to primary feed), proceeding...")

        if UniversalActions(device)._check_if_no_posts():
            UniversalActions(device)._reload_page()
            if UniversalActions(device)._check_if_no_posts():
                return False

    target_view = TargetView(device)
    result_view = target_view._getRecyclerView()
    first_image_in_view = (
        target_view._getFirstImageView(result_view)
        if hasattr(target_view, "_getFirstImageView")
        else target_view._getFistImageView(result_view)
    )
    if first_image_in_view.exists():
        logger.info(f"Opening the first result for {target}.")
        opened_post_view = OpenedPostView(device)
        for attempt in range(2):
            try:
                bounds = first_image_in_view.get_bounds()
                x_center = (bounds["left"] + bounds["right"]) // 2
                y_center = (bounds["top"] + bounds["bottom"]) // 2
                if hasattr(device, "deviceV2") and hasattr(device.deviceV2, "click"):
                    device.deviceV2.click(x_center, y_center)
                else:
                    first_image_in_view.click()
            except Exception:
                first_image_in_view.click()

            random_sleep(inf=1, sup=2, modulable=False)

            if opened_post_view.is_peek_preview_opened():
                logger.info("Peek Preview detected on thumbnail. Dismissing...")
                opened_post_view.dismiss_peek()

            if opened_post_view.is_post_opened():
                logger.info(f"First post for {target} successfully opened.")
                return True

            if attempt == 0:
                logger.debug("Post did not open on first tap, retrying tap...")
                first_image_in_view = (
                    target_view._getFirstImageView(result_view)
                    if hasattr(target_view, "_getFirstImageView")
                    else target_view._getFistImageView(result_view)
                )
                if not first_image_in_view.exists():
                    break

        logger.warning(
            f"Failed to open first post for {target}: thumbnail tap did not navigate to post view."
        )
        return False
    else:
        logger.info(
            f"There is any result for {target} (not exists or doesn't load). Skip."
        )
        return False


def nav_to_post_likers(device, username, my_username):
    """navigate to blogger post likers"""
    if username == my_username:
        TabBarView(device).navigateToProfile()
    else:
        search_view = TabBarView(device).navigateToSearch()
        if not search_view.navigate_to_target(username, "account"):
            return False
    profile_view = ProfileView(device)
    is_private = profile_view.isPrivateAccount()
    posts_count = profile_view.getPostsCount()
    is_empty = posts_count == 0
    if is_private or is_empty:
        private_empty = "Private" if is_private else "Empty"
        logger.info(f"{private_empty} account.", extra={"color": f"{Fore.GREEN}"})
        return False
    logger.info(f"Opening the first post of {username}.")
    ProfileView(device).swipe_to_fit_posts()
    opened_post_view, _, _ = PostsGridView(device).navigateToPost(0, 0)
    if opened_post_view is None:
        logger.warning("Couldn't open the first post. Skip.")
        return False
    return True


def nav_to_feed(device):
    TabBarView(device).navigateToHome()

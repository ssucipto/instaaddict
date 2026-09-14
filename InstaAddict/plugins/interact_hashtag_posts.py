import logging
from functools import partial
from random import seed

import emoji
from colorama.ansi import Fore

from InstaAddict.core.decorators import run_safely
from InstaAddict.core.handle_sources import handle_posts
from InstaAddict.core.interaction import (
    interact_with_user,
    is_follow_limit_reached_for_source,
)
from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.utils import get_value, init_on_things, sample_sources

logger = logging.getLogger(__name__)

# Script Initialization
seed()


class InteractHashtagPosts(Plugin):
    """Handles the functionality of interacting with a hashtags post owners"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Handles the functionality of interacting with a hashtags post owners"
        )
        self.arguments = [
            {
                "arg": "--hashtag-posts-recent",
                "nargs": "+",
                "help": "interact to hashtag post owners in recent tab",
                "metavar": ("hashtag1", "hashtag2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--hashtag-posts-top",
                "nargs": "+",
                "help": "interact to hashtag post owners in top tab",
                "metavar": ("hashtag1", "hashtag2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--expand-hashtags",
                "action": "store_true",
                "help": "dynamically expand hashtags via AI Gemini model",
                "default": False,
            },
            {
                "arg": "--no-harvest-hashtags",
                "action": "store_true",
                "help": "disable harvesting new hashtags from encountered post captions",
                "default": False,
            },
            {
                "arg": "--hashtags-file",
                "nargs": "?",
                "help": "custom path to hashtags.yml (defaults to accounts/<username>/hashtags.yml)",
                "metavar": "hashtags.yml",
                "default": None,
            },
        ]

    def run(self, device, configs, storage, sessions, profile_filter, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.device_id = configs.args.device
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.args = configs.args
        self.current_mode = plugin

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        raw_sources = (
            self.args.hashtag_posts_top
            if self.current_mode == "hashtag-posts-top"
            else self.args.hashtag_posts_recent
        )
        sources = []
        for s in (raw_sources or []):
            if isinstance(s, str):
                for item in s.split():
                    sources.append(item)
            else:
                sources.append(s)

        from InstaAddict.core.hashtag_manager import HashtagManager

        manager = HashtagManager.get_instance(
            username=self.session_state.my_username,
            hashtags_file=getattr(self.args, "hashtags_file", None),
        )

        # Strategy 1: AI Gemini Expansion if requested
        if getattr(self.args, "expand_hashtags", False):
            try:
                ai_persona = getattr(configs, "ai_persona", None) or getattr(
                    self.args, "ai_persona", None
                )
                added = manager.expand_via_gemini(persona=ai_persona)
                logger.info(
                    f"HashtagManager: Gemini AI expanded {len(added)} new candidates."
                )
            except Exception as e:
                logger.warning(f"HashtagManager: Gemini expansion failed: {e}")

        # Strategy 2 & Masterlist: Sample from tiered pool if available, else fallback
        if manager.has_tiered_sources():
            truncate_count = get_value(self.args.truncate_sources, None, None)
            sampled_sources = manager.get_session_sources(
                fallback_sources=sources,
                total_limit=int(truncate_count) if truncate_count else None,
            )
            logger.info(
                f"HashtagManager active: sampled {len(sampled_sources)} tiered hashtags: {sampled_sources}"
            )
            effective_sources = sampled_sources
        else:
            effective_sources = sample_sources(sources, self.args.truncate_sources)

        # Start
        for source in effective_sources:
            (
                active_limits_reached,
                _,
                actions_limit_reached,
            ) = self.session_state.check_limit(limit_type=self.session_state.Limit.ALL)
            limit_reached = active_limits_reached or actions_limit_reached

            self.state = State()
            if source[0] != "#":
                source = "#" + source
            logger.info(
                f"Handle {emoji.emojize(source, use_aliases=True)}",
                extra={"color": f"{Fore.BLUE}"},
            )

            # Init common things
            (
                on_interaction,
                stories_percentage,
                likes_percentage,
                follow_percentage,
                comment_percentage,
                pm_percentage,
                interact_percentage,
            ) = init_on_things(source, self.args, self.sessions, self.session_state)

            @run_safely(
                device=device,
                device_id=self.device_id,
                sessions=self.sessions,
                session_state=self.session_state,
                screen_record=self.args.screen_record,
                configs=configs,
            )
            def job():
                self.handle_hashtag(
                    device,
                    source,
                    plugin,
                    storage,
                    profile_filter,
                    on_interaction,
                    stories_percentage,
                    likes_percentage,
                    follow_percentage,
                    comment_percentage,
                    pm_percentage,
                    interact_percentage,
                )
                self.state.is_job_completed = True

            while not self.state.is_job_completed and not limit_reached:
                job()

            if limit_reached:
                logger.info("Ending session.")
                self.session_state.check_limit(
                    limit_type=self.session_state.Limit.ALL, output=True
                )
                break

    def handle_hashtag(
        self,
        device,
        hashtag,
        current_job,
        storage,
        profile_filter,
        on_interaction,
        stories_percentage,
        likes_percentage,
        follow_percentage,
        comment_percentage,
        pm_percentage,
        interact_percentage,
    ):
        interaction = partial(
            interact_with_user,
            my_username=self.session_state.my_username,
            likes_count=self.args.likes_count,
            likes_percentage=likes_percentage,
            stories_percentage=stories_percentage,
            follow_percentage=follow_percentage,
            comment_percentage=comment_percentage,
            pm_percentage=pm_percentage,
            profile_filter=profile_filter,
            args=self.args,
            session_state=self.session_state,
            scraping_file=self.args.scrape_to_file,
            current_mode=self.current_mode,
        )

        source_follow_limit = (
            get_value(self.args.follow_limit, None, 15)
            if self.args.follow_limit is not None
            else None
        )
        is_follow_limit_reached = partial(
            is_follow_limit_reached_for_source,
            session_state=self.session_state,
            follow_limit=source_follow_limit,
            source=hashtag,
        )

        handle_posts(
            self,
            device,
            self.session_state,
            hashtag,
            current_job,
            storage,
            profile_filter,
            on_interaction,
            interaction,
            is_follow_limit_reached,
            interact_percentage,
            self.args.scrape_to_file,
        )

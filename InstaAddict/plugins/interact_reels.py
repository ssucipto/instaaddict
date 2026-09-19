import logging
import random
from time import sleep

from colorama import Fore
from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.views import TabBarView, UniversalActions, Direction
from InstaAddict.core.interaction import _comment
from InstaAddict.core.utils import random_sleep
from InstaAddict.core.gemini_vision import evaluate_and_comment_reel

logger = logging.getLogger(__name__)


class InteractReelsPlugin(Plugin):
    """Interacts dynamically with the Instagram Reels explore algorithm"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Interacts dynamically with the Instagram Reels explore algorithm"
        )
        self.arguments = [
            {
                "arg": "--interact-reels",
                "nargs": "?",
                "const": "10-20",
                "help": (
                    "Number of Reels to watch, like, and comment on "
                    "before moving on"
                ),
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--evaluate-percentage",
                "nargs": None,
                "help": "Percentage of Reels to evaluate with Vision AI",
                "metavar": "25",
                "default": 25,
                "type": int,
            },
            {
                "arg": "--reels-topic",
                "metavar": "dogs or animals",
                "default": "dogs or animals",
                "help": "Target topic or niche for Gemini Vision AI Reel evaluation",
            },
        ]

    def run(self, device, configs, storage, sessions, profile_filter, plugin):
        amount = configs.args.interact_reels
        if not amount:
            return

        from InstaAddict.core.decorators import run_safely
        from InstaAddict.core.utils import get_value
        from InstaAddict.core.watchdog import record_heartbeat

        target_amount = get_value(amount, "Interact Reels limit: {}", 2)

        session_state = sessions[-1] if sessions and len(sessions) > 0 else None

        @run_safely(
            device=device,
            device_id=getattr(configs, "device_id", None),
            sessions=sessions,
            session_state=session_state,
            screen_record=getattr(configs.args, "screen_record", False) if hasattr(configs, "args") else False,
            configs=configs,
        )
        def job():
            tab_bar = TabBarView(device)
            tab_bar.navigateToReels()
            logger.info("Engaging Automated Reels Stalker...")

            d = device.deviceV2

            ad_cta_regex = (
                "(?i)^(Learn More|Install Now|Install|Shop Now|Download|"
                "Sign Up|Watch More|Apply Now|Get Offer|Book Now|"
                "Contact Us|Play Game|Subscribe|Open app)$"
            )

            for i in range(target_amount):
                record_heartbeat(
                    "interact-reels",
                    f"Watching Reel {i+1}/{target_amount}",
                )
                try:
                    from InstaAddict.core.tui import DashboardManager

                    if DashboardManager.is_active():
                        dm = DashboardManager.get_instance()
                        if dm.state.is_skip_task_requested():
                            logger.warning(
                                "[TUI] Task skip requested by user ([CTRL+S]). Exiting interact-reels early...",
                                extra={"color": f"{Fore.YELLOW}"},
                            )
                            break
                        if dm.state.is_upload_requested():
                            logger.info(
                                "[TUI] Immediate upload requested by user ([CTRL+U]). Exiting interact-reels to execute upload...",
                                extra={"color": f"{Fore.MAGENTA}"},
                            )
                            break
                except Exception:
                    pass

                logger.info(f"Watching Reel {i+1}/{target_amount}...")

                if sessions and len(sessions) > 0:
                    if hasattr(sessions[-1], "increment_reels_evaluated"):
                        sessions[-1].increment_reels_evaluated()
                    sessions[-1].totalWatched = getattr(sessions[-1], "totalWatched", 0) + 1
                try:
                    from InstaAddict.core.tui import DashboardManager

                    if DashboardManager.is_active():
                        dm = DashboardManager.get_instance()
                        dm.state.update_activity(
                            job="interact-reels",
                            action=f"Evaluating Reel {i+1}/{target_amount}...",
                        )
                        dm.update_render()
                except Exception:
                    pass

                w, h = d.info["displayWidth"], d.info["displayHeight"]

                # Anti-Ad Trapping Mechanism

                # 1. First, check if accidentally clicked INTO the ad
                if UniversalActions.escape_in_app_browser(device):
                    logger.info("Flinging away from the Ad Reel...")
                    device.swipe(Direction.UP, 0.85)
                    random_sleep(2, 4)
                    continue

                # 2. Check if current reel itself is an ad
                ad_button = device.find(textMatches=ad_cta_regex)
                sponsored = device.find(textMatches="(?i)^Sponsored$")
                if (
                    ad_button.exists(ui_timeout=1)
                    or sponsored.exists(ui_timeout=1)
                ):
                    if sessions and len(sessions) > 0 and hasattr(sessions[-1], "increment_ads_bypassed"):
                        sessions[-1].increment_ads_bypassed()
                    logger.warning(
                        "Sponsored Advertisement detected. Flinging away..."
                    )
                    device.swipe(Direction.UP, 0.85)
                    random_sleep(2, 4)
                    continue

                # Brief pause to let video render for classification
                sleep(2)

                # 1. THROTTLE & FILTER
                eval_pct = int(getattr(configs.args, "evaluate_percentage", None) or 70)
                if random.randint(1, 100) > eval_pct:
                    logger.info("Skipping reel evaluation to preserve quota.")
                    device.swipe(Direction.UP, 0.85)
                    random_sleep(2, 4)
                    continue

                raw_png = d.screenshot(format="raw")
                reels_topic = getattr(configs.args, "reels_topic", None) or "dogs or animals"
                comment_text = evaluate_and_comment_reel(
                    raw_png, topic=reels_topic
                )

                if comment_text:
                    logger.info(
                        "🐾 Vision AI Detected Target! Engaging with target..."
                    )
                    random_sleep(10, 25)

                    # Double Tap to Like
                    d.click(w // 2, h // 2)
                    sleep(0.1)
                    d.click(w // 2, h // 2)
                    logger.info("Liked Reel via double-tap.")
                    UniversalActions.detect_block(device)
                    if sessions and len(sessions) > 0:
                        sessions[-1].totalLikes = getattr(sessions[-1], "totalLikes", 0) + 1

                    # Optional Follow Reel Creator
                    follow_pct = int(getattr(configs.args, "follow_percentage", None) or 0)
                    followed_creator = False
                    if follow_pct > 0 and random.randint(1, 100) <= follow_pct:
                        if sessions and len(sessions) > 0 and not sessions[-1].check_limit(
                            limit_type=sessions[-1].Limit.FOLLOWS, output=False
                        ):
                            follow_btn = device.find(
                                resourceIdMatches=".*clips_follow_button.*|.*follow_button.*",
                                textMatches="(?i)^Follow$"
                            )
                            if not follow_btn.exists():
                                follow_btn = device.find(
                                    descriptionMatches="(?i)^Follow$"
                                )
                            if not follow_btn.exists():
                                follow_btn = device.find(
                                    textMatches="(?i)^Follow$"
                                )
                            if follow_btn.exists():
                                follow_btn.click()
                                sleep(1.0)
                                UniversalActions.detect_block(device)
                                logger.info(
                                    "Followed Reel creator! 🐾",
                                    extra={"color": f"{Fore.GREEN}"}
                                )
                                sessions[-1].totalFollowed = (
                                    getattr(sessions[-1], "totalFollowed", 0) + 1
                                )
                                followed_creator = True

                    if sessions and len(sessions) > 0:
                        sessions[-1].add_interaction(
                            "interact-reels",
                            succeed=True,
                            followed=followed_creator,
                            scraped=False,
                        )

                    try:
                        from InstaAddict.core.views import MediaType

                        current_user = getattr(sessions[-1], "my_username", None) if sessions else None
                        _comment(
                            device,
                            my_username=current_user or "REEL_STALKER",
                            comment_percentage=100,
                            args=configs.args,
                            session_state=sessions[-1],
                            media_type=MediaType.REEL,
                            explicit_comment=comment_text,
                        )
                    except Exception as e:
                        logger.error(f"Reels Stalker Comment Error: {e}")
                else:
                    logger.info(
                        "⏭️ Non-Target Reel. Skipping to train algorithm!"
                    )
                    random_sleep(1, 2)

                # 2. FIXED ADVANCED SWIPE (Avoid rubber-banding)
                logger.info("Swiping to next Reel...")
                device.swipe(Direction.UP, 0.85)
                random_sleep(2, 4)

        job()

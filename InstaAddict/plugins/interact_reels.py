import logging
import re
from random import seed
from time import sleep

from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.views import TabBarView, UniversalActions, Direction
from InstaAddict.core.interaction import _comment
from InstaAddict.core.utils import random_sleep
from InstaAddict.core.gemini_vision import evaluate_and_comment_reel
import random

logger = logging.getLogger(__name__)

class InteractReelsPlugin(Plugin):
    """Interacts dynamically with the Instagram Reels explore algorithm"""

    def __init__(self):
        super().__init__()
        self.description = "Interacts dynamically with the Instagram Reels explore algorithm"
        self.arguments = [
            {
                "arg": "--interact-reels",
                "nargs": "?",
                "const": "10-20",
                "help": "Number of Reels to watch, like, and comment on before moving on",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--evaluate-percentage",
                "help": "Percentage of Reels to evaluate with Vision AI",
                "metavar": "25",
                "default": 25,
                "type": int,
            }
        ]

    def run(self, device, configs, storage, sessions, profile_filter, plugin):
        amount = configs.args.interact_reels
        if not amount:
            return

        from InstaAddict.core.utils import get_value
        target_amount = get_value(amount, "Interact Reels limit: {}", 2)

        tab_bar = TabBarView(device)
        tab_bar.navigateToReels()
        logger.info("Engaging Automated Reels Stalker...")
        
        universal = UniversalActions(device)
        d = device.deviceV2
        
        for i in range(target_amount):
            logger.info(f"Watching Reel {i+1}/{target_amount}...")
            
            w, h = d.info['displayWidth'], d.info['displayHeight']
            

            # Anti-Ad Trapping Mechanism
            
            # 1. First, check if we accidentally clicked INTO the ad (webview mode)
            webview = device.find(className="android.webkit.WebView")
            if webview.exists(ui_timeout=1):
                logger.warning("Trapped in an Ad Webview! Escaping via BACK...")
                device.back()
                sleep(3)
                logger.info("Flinging away from the Ad Reel...")
                device.swipe(Direction.UP, 0.85)
                random_sleep(2, 4)
                continue
                
            # 2. Check if the current reel itself IS an ad (has a 'Learn More', 'Install', or 'Shop Now' button)
            ad_button = device.find(textMatches="(?i)(Learn More|Install|Shop Now|Download)")
            sponsored = device.find(textMatches="(?i)Sponsored")
            if ad_button.exists(ui_timeout=1) or sponsored.exists(ui_timeout=1):
                logger.warning("Sponsored Advertisement detected. Flinging away to avoid trap...")
                device.swipe(Direction.UP, 0.85)
                random_sleep(2, 4)
                continue
                
            # Brief pause to let video render for classification
            sleep(2)
            
            # 1. THROTTLE & FILTER
            eval_pct = getattr(configs.args, 'evaluate_percentage', 25)
            if random.randint(1, 100) > eval_pct:
                logger.info("Skipping reel evaluation to preserve quota.")
                device.swipe(Direction.UP, 0.85)
                random_sleep(2, 4)
                continue

            raw_png = d.screenshot(format='raw')
            comment_text = evaluate_and_comment_reel(raw_png, topic=configs.args.reels_topic or "dogs or animals")
            
            if comment_text:
                logger.info("?? Vision AI Detected Animal! Engaging with targeting algorithm...")
                random_sleep(10, 25)

                # Double Tap to Like
                d.click(w // 2, h // 2)
                sleep(0.1)
                d.click(w // 2, h // 2)
                logger.info("Liked Reel via double-tap.")

                try:
                    from InstaAddict.core.views import MediaType
                    _comment(
                        device,
                        my_username="REEL_STALKER",
                        comment_percentage=100,
                        args=configs.args,
                        session_state=sessions[-1],
                        media_type=MediaType.REEL,
                        explicit_comment=comment_text
                    )
                except Exception as e:
                    import traceback
                    logger.error(f"Reels Stalker Comment Error: {e}")
            else:
                logger.info("?? Non-Animal Reel. Skipping immediately to train our feed algorithm!")
                random_sleep(1, 2)

            # 2. FIXED ADVANCED SWIPE (Avoid rubber-banding)
            logger.info("Swiping to next Reel...")
            # Use native structural swipe to ensure adequate momentum physics.
            device.swipe(Direction.UP, 0.85)
            
            # Anti-rubber-band grace period
            random_sleep(2, 4)
            
        logger.info("Reels Stalker job completed! Returning Home.")
        tab_bar.navigateToHome()


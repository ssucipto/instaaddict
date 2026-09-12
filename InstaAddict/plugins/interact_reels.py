import logging
from random import seed
from time import sleep

from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.views import TabBarView, UniversalActions, Direction
from InstaAddict.core.interaction import _comment
from InstaAddict.core.utils import random_sleep
from InstaAddict.core.gemini_vision import evaluate_reel_content

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
            # Brief pause to let video render for classification
            sleep(2)
            
            # 1. SCREENSHOT & FILTER
            raw_png = d.screenshot(format='raw')
            is_valid_topic = evaluate_reel_content(raw_png, topic="dogs, puppies, or animals")
            
            w, h = d.info['displayWidth'], d.info['displayHeight']
            
            if is_valid_topic:
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
                        media_type=MediaType.REEL
                    )
                except Exception as e:
                    import traceback
                    logger.error(f"Reels Stalker Comment Error: {e}")
            else:
                logger.info("?? Non-Animal Reel. Skipping immediately to train our feed algorithm!")
                random_sleep(1, 2)

            # 2. FIXED ADVANCED SWIPE (Avoid rubber-banding)
            logger.info("Swiping to next Reel...")
            # We use absolute coordinates with a rapid swipe (duration=0.05) to ensure it triggers the page-flip 
            # rather than a slow scroll that springs back.
            d.swipe(w // 2, int(h * 0.8), w // 2, int(h * 0.1), 0.05)
            
            # Anti-rubber-band grace period
            random_sleep(2, 4)
            
        logger.info("Reels Stalker job completed! Returning Home.")
        tab_bar.navigateToHome()


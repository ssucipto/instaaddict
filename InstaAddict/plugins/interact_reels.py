import logging
from random import seed
from time import sleep

from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.views import TabBarView, UniversalActions, Direction
from InstaAddict.core.interaction import _comment
from InstaAddict.core.utils import random_sleep

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
            # Enforced Temporal Video Bounds (Doom Scrolling Simulation)
            random_sleep(12, 35)

            # Double Tap to Like
            w, h = d.info['displayWidth'], d.info['displayHeight']
            d.click(w // 2, h // 2)
            sleep(0.1)
            d.click(w // 2, h // 2)
            logger.info("Liked Reel via double-tap.")

            # Trigger AI Contextual Comment
            # Passing MediaType.REEL (value 3 natively in most enums but we can just pass literal)
            # We call the modified `_comment` function natively hooking our Vision AI
            try:
                from InstaAddict.core.views import MediaType
                # Note: args expects comment_percentage mapping, we bypass by giving native truthy
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
                logger.error(f"Reels Stalker Comment Error: {e}\n{traceback.format_exc()}")

            # Swipe to next reel natively
            logger.info("Swiping to next Reel...")
            universal._swipe_points(direction=Direction.UP, delta_y=600)
            random_sleep(1, 3)
            
        logger.info("Reels Stalker job completed! Returning Home.")
        tab_bar.navigateToHome()

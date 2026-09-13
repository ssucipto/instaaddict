import re

file_path = 'InstaAddict/plugins/interact_reels.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Instagram updated its architecture to nest a 'VIDEO_CONTAINER' fallback on advertisements instead of entirely dropping the element.
# We'll explicitly scrape the active hierarchy text instead of just relying on ID bounds. if we see buttons like "Learn More", it's an ad.
new_code = """
            # Anti-Ad Trapping Mechanism
            from InstaAddict.core.utils import case_insensitive_re
            
            # 1. First, check if we accidentally clicked INTO the ad (webview mode)
            webview = device.find(className="android.webkit.WebView")
            if webview.exists(ui_timeout=1):
                logger.warning("Trapped in an Ad Webview! Escaping via BACK...")
                device.back()
                sleep(3)
                logger.info("Flinging away from the Ad Reel...")
                device.swipe(Direction.UP, 0.7)
                random_sleep(2, 4)
                continue
                
            # 2. Check if the current reel itself IS an ad (has a 'Learn More', 'Install', or 'Shop Now' button)
            ad_button = device.find(textMatches=re.compile(r"(Learn More|Install|Shop Now|Download)", re.IGNORECASE))
            sponsored = device.find(textMatches=re.compile(r"Sponsored", re.IGNORECASE))
            if ad_button.exists(ui_timeout=1) or sponsored.exists(ui_timeout=1):
                logger.warning("Sponsored Advertisement detected. Flinging away to avoid trap...")
                device.swipe(Direction.UP, 0.7)
                random_sleep(2, 4)
                continue
"""

text = text.replace("""
            # Anti-Ad Trapping Mechanism
            import re
            from InstaAddict.core.resources import ResourceID
            # Build the regex manually to avoid import errors
            clips = device.find(resourceIdMatches=re.compile(r"^%s$" % ResourceID.CLIPS_VIDEO_CONTAINER, re.IGNORECASE))

            if not clips.exists():
                logger.warning("Reels UI Missing! Trapped in an Ad Webview. Escaping via BACK...")
                device.back()
                sleep(3)
                logger.info("Flinging away from the Ad Reel...")
                device.swipe(Direction.UP, 0.7)
                random_sleep(2, 4)
                continue
""", new_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

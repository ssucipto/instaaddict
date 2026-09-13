import re

file_path = 'InstaAddict/plugins/interact_reels.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# I will replace the escape hatch to swipe.
escape_code_old = """            if not clips.exists():
                logger.warning("Reels UI Missing! Trapped in an Ad Webview. Escaping via BACK...")
                device.back()
                sleep(3)"""

escape_code_new = """            if not clips.exists():
                logger.warning("Reels UI Missing! Trapped in an Ad Webview. Escaping via BACK...")
                device.back()
                sleep(3)
                logger.info("Flinging away from the Ad Reel...")
                d.swipe(w // 2, int(h * 0.8), w // 2, int(h * 0.1), 0.05)
                random_sleep(2, 4)
                continue"""

text = text.replace(escape_code_old, escape_code_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

import re

file_path = 'InstaAddict/core/device_facade.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Completely neutralize momentum on coordinate math swipes by forcing a drag instead of a swipe
old_code = """        try:
            logger.debug(f"Swipe from: ({sx},{sy}) to ({ex},{ey}).")
            self.deviceV2.swipe_points([[sx, sy], [ex, ey]], uniform(0.12, 0.18))
            DeviceFacade.sleep_mode(SleepTime.TINY)"""

new_code = """        try:
            logger.debug(f"Drag (No-Fling) from ({sx},{sy}) to ({ex},{ey}).")
            self.deviceV2.drag(sx, sy, ex, ey, duration=0.25)
            DeviceFacade.sleep_mode(SleepTime.TINY)"""

text = text.replace(old_code, new_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

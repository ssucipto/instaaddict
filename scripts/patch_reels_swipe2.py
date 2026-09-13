import re

file_path = 'InstaAddict/plugins/interact_reels.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('d.swipe(w // 2, int(h * 0.8), w // 2, int(h * 0.1), 0.05)', 'device.swipe(Direction.UP, 0.7)')
# Fix the comments above the second swipe so it's accurate
text = text.replace('# We use absolute coordinates with a rapid swipe (duration=0.05) to ensure it triggers the page-flip \n            # rather than a slow scroll that springs back.', '# Use native structural swipe to ensure adequate momentum physics.')
text = text.replace('??', '??')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

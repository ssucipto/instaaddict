import re

file_path = 'InstaAddict/plugins/interact_reels.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('d.swipe(w // 2, int(h * 0.8), w // 2, int(h * 0.1), 0.05)', 'device.swipe(Direction.UP, 0.7)')
# also need to make sure Direction is imported, wait, let's check imports

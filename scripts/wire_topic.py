import re

file_path = 'InstaAddict/plugins/interact_reels.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace hardcoded "dogs, puppies, or animals" with dynamic configs.args.reels_topic
text = text.replace('topic="dogs, puppies, or animals"', 'topic=configs.args.reels_topic or "dogs or animals"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

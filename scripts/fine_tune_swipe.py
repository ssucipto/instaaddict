import re

file_path = 'InstaAddict/core/device_facade.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fine-tuning the swipe momentum down to 0.12 - 0.18
text = text.replace('uniform(0.20, 0.35)', 'uniform(0.12, 0.18)')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

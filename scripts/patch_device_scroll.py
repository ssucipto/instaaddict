import re

file_path = 'InstaAddict/core/device_facade.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("uniform(0.05, 0.15)", "uniform(0.20, 0.35)")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

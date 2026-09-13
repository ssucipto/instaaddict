import re

file_path = 'InstaAddict/core/device_facade.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change the hardcoded duration in swipe_points to a much faster scroll speed
# from uniform(0.2, 0.5) to uniform(0.05, 0.15)
new_content = content.replace("uniform(0.2, 0.5)", "uniform(0.05, 0.15)")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

import re

file_path = 'InstaAddict/core/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# I am going to replace the coordinate based obj2 calculation 
# which causes the halfway scrolling error.
text = text.replace(
    'obj2 = (media_bounds["bottom"] + media_bounds["top"]) * 1 / 3',
    'obj2 = (media_bounds["bottom"] + media_bounds["top"]) * 1 / 3\n            if ac_exists: obj2 = ac_bottom + 10'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

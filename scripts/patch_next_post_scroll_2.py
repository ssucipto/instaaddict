import re

file_path = 'InstaAddict/core/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix NEXT_POST obj2
old_code = """            obj2 = (media_bounds["bottom"] + media_bounds["top"]) * 1 / 3
            if ac_exists: obj2 = ac_bottom + 10"""

new_code = """            ac_exists, _, ac_bottom = PostsViewList(self.device)._get_action_bar_position()
            if ac_exists:
                obj2 = ac_bottom + 20
            else:
                obj2 = media_bounds["top"] if media_bounds else displayHeight * 0.25"""

text = text.replace(old_code, new_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

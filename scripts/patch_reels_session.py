import re

with open('InstaAddict/plugins/interact_reels.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'session_state=sessions,',
    'session_state=sessions[-1],'
)

with open('InstaAddict/plugins/interact_reels.py', 'w', encoding='utf-8') as f:
    f.write(code)

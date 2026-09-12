import re

with open('InstaAddict/plugins/upload_posts.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace('"ai-caption-persona"', '"ai-persona"')

with open('InstaAddict/plugins/upload_posts.py', 'w', encoding='utf-8') as f:
    f.write(code)

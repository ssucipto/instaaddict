import re

with open('InstaAddict/core/gemini_vision.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_idemp = """_RECENT_INTERACTIONS = set()"""
new_idemp = """import json
_HISTORY_FILE = "ai_comment_history.json"
_RECENT_INTERACTIONS = set()

if os.path.exists(_HISTORY_FILE):
    try:
        with open(_HISTORY_FILE, "r") as f:
            _RECENT_INTERACTIONS = set(json.load(f))
    except:
        pass"""

code = code.replace(old_idemp, new_idemp)

old_update = """    SESSION_API_CALLS += 1
    _RECENT_INTERACTIONS.add(author_username)"""
new_update = """    SESSION_API_CALLS += 1
    _RECENT_INTERACTIONS.add(author_username)
    try:
        with open(_HISTORY_FILE, "w") as f:
            json.dump(list(_RECENT_INTERACTIONS), f)
    except:
        pass"""

code = code.replace(old_update, new_update)

with open('InstaAddict/core/gemini_vision.py', 'w', encoding='utf-8') as f:
    f.write(code)

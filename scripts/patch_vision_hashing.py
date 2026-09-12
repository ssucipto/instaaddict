import re

with open('InstaAddict/core/gemini_vision.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Change function signature
code = code.replace("def get_vision_comment(device, author_username: str) -> str:", "def get_vision_comment(device, _reserved: str = '') -> str:")

# Replace author_username logic with image hashing
old_idemp_check = """
    if author_username in _RECENT_INTERACTIONS:
        logger.warning(f"Idempotency Guard: Already attempted to comment on {author_username} this session.")
        return ""

    SESSION_API_CALLS += 1
    _RECENT_INTERACTIONS.add(author_username)"""

new_idemp_check = """
    try:
        raw_screenshot = device.deviceV2.screenshot(format='raw')
    except:
        return ""
        
    import hashlib
    # Create an optical hash of a small chunk of the screen to identify this Reel across sessions
    screen_hash = hashlib.md5(raw_screenshot[:1024]).hexdigest()

    if screen_hash in _RECENT_INTERACTIONS:
        logger.warning(f"Idempotency Guard: Already commented on this optical hash {screen_hash}. Skipping.")
        return ""

    SESSION_API_CALLS += 1
    _RECENT_INTERACTIONS.add(screen_hash)"""

code = code.replace(old_idemp_check, new_idemp_check)

# Remove the screenshot line from the TRY block since we moved it above
code = code.replace("raw_screenshot = device.deviceV2.screenshot(format='raw')", "")

with open('InstaAddict/core/gemini_vision.py', 'w', encoding='utf-8') as f:
    f.write(code)

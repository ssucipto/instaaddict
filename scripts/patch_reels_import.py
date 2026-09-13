import re

file_path = 'InstaAddict/plugins/interact_reels.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the import structure. `case_insensitive_re` comes from `InstaAddict.core.resources` in older gramaddict versions
# Actually let's just write the regex inline to avoid versioning hell.

fix_code = """
            # Anti-Ad Trapping Mechanism
            import re
            from InstaAddict.core.resources import ResourceID
            # Build the regex manually to avoid import errors
            clips = device.find(resourceIdMatches=re.compile(r"^%s$" % ResourceID.CLIPS_VIDEO_CONTAINER, re.IGNORECASE))
"""

text = text.replace("""            # Anti-Ad Trapping Mechanism
            from InstaAddict.core.resources import ResourceID
            from InstaAddict.core.utils import case_insensitive_re
            clips = device.find(resourceIdMatches=case_insensitive_re(ResourceID.CLIPS_VIDEO_CONTAINER))""", fix_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

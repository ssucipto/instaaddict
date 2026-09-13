import io

with open('InstaAddict/core/gemini_vision.py', 'rb') as f:
    raw = f.read()

# Replace UTF-16 null bytes if any
# Better yet, since we know it was clean before, let's just strip null bytes entirely for now
# or better yet, read the file, decode ignoring errors, and write back.
raw = raw.replace(b'\x00', b'')

with open('InstaAddict/core/gemini_vision.py', 'wb') as f:
    f.write(raw)

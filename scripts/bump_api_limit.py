import re

file_path = 'InstaAddict/core/gemini_vision.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the MAX_API_CALLS constant
text = re.sub(r'MAX_API_CALLS_PER_SESSION\s*=\s*50', 'MAX_API_CALLS_PER_SESSION = 400', text)

# also replace the log message just in case
text = text.replace('limit of 50 calls', 'limit of 400 calls')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

import re

with open('InstaAddict/core/gemini_vision.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")',
    'warnings.simplefilter("ignore")'
)

with open('InstaAddict/core/gemini_vision.py', 'w', encoding='utf-8') as f:
    f.write(code)

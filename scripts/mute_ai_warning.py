import re
with open('InstaAddict/core/gemini_vision.py', 'r', encoding='utf-8') as f:
    code = f.read()

suppress = """import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
import google.generativeai as genai"""

code = code.replace("import google.generativeai as genai", suppress)

with open('InstaAddict/core/gemini_vision.py', 'w', encoding='utf-8') as f:
    f.write(code)

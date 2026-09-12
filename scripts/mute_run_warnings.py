import re

with open('run.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Insert warnings silencer at the very beginning
if "warnings.filterwarnings" not in code:
    silencer = """import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
"""
    code = silencer + code

with open('run.py', 'w', encoding='utf-8') as f:
    f.write(code)

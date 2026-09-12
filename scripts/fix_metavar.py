import re

with open('InstaAddict/plugins/core_arguments.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add the missing 'metavar' key
old_dict = """            {
                "arg": "--ai-persona",
                "help": "System persona identity for Gemini Vision AI comments and captions",
                "nargs": "?",
                "const": "casual Instagram user",
                "default": "casual Instagram user",
            },"""

new_dict = """            {
                "arg": "--ai-persona",
                "help": "System persona identity for Gemini Vision AI comments and captions",
                "nargs": "?",
                "const": "casual Instagram user",
                "default": "casual Instagram user",
                "metavar": "persona string",
            },"""

code = code.replace(old_dict, new_dict)

with open('InstaAddict/plugins/core_arguments.py', 'w', encoding='utf-8') as f:
    f.write(code)

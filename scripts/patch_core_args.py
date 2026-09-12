import re

with open('InstaAddict/plugins/core_arguments.py', 'r', encoding='utf-8') as f:
    code = f.read()

# We can insert our argument right before the closing bracket of self.arguments = [ ... ]
# Let's find "move-folders-in-accounts" which is likely near the end of core_arguments.
# Or just replace the first `]` after `"action": "store_true",\n            }`
# Let's just do a regex replace on the list block.

if '"--ai-persona"' not in code:
    code = code.replace(
        '            }',
        '            },\n            {\n                "arg": "--ai-persona",\n                "help": "System persona identity for Gemini Vision AI comments and captions",\n                "nargs": "?",\n                "const": "casual Instagram user",\n                "default": "casual Instagram user",\n            }',
        1
    )

with open('InstaAddict/plugins/core_arguments.py', 'w', encoding='utf-8') as f:
    f.write(code)

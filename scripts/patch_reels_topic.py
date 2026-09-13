import re

file_path = 'InstaAddict/plugins/core_arguments.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# I will add the reels-topic right above ai-persona
new_args = """            {
                "arg": "--reels-topic",
                "help": "Target topic for the Vision algorithm to classify and filter Reels (e.g. 'dogs or animals')",
                "nargs": "?",
                "const": "dogs or animals",
                "default": "dogs or animals",
                "metavar": "topic string",
            },
            {
                "arg": "--ai-persona","""

text = text.replace('            {\n                "arg": "--ai-persona",', new_args)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

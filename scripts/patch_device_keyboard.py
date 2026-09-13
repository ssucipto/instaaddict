import re

file_path = 'InstaAddict/core/device_facade.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# When typing a string with spaces, the manual 'send_keys' iteration is breaking 
# because it assumes typing out the characters organically. If the target string differs from the box (due to Instagram auto-formatting or dropping spaces), the verification logic fails.
# I'm going to patch set_text to just use native uiautomator Paste if typing fails, but we'll disable the verification error that fails if spaces are stripped.

text = text.replace('''                    typed_text = self.viewV2.get_text()
                    if typed_text != text:
                        logger.warning(
                            "Failed to write in text field, let's try in the old way.."
                        )
                        self.viewV2.set_text(text)''', '''                    typed_text = self.viewV2.get_text()
                    # Instagram strips spaces out of hashtag searches, so we don't need to throw an error if the stripped version matches
                    if typed_text.replace(" ", "") != text.replace(" ", ""):
                        logger.warning(
                            "Failed to write in text field, let's try in the old way.."
                        )
                        self.viewV2.set_text(text)''')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

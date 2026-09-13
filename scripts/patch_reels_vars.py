import re

file_path = 'InstaAddict/plugins/interact_reels.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Pull w and h up before the clips check
fix_code = """        for i in range(target_amount):
            logger.info(f"Watching Reel {i+1}/{target_amount}...")
            
            w, h = d.info['displayWidth'], d.info['displayHeight']
            
            # Anti-Ad Trapping Mechanism
            from InstaAddict.core.resources import ResourceID"""

text = text.replace("""        for i in range(target_amount):
            logger.info(f"Watching Reel {i+1}/{target_amount}...")
            
            # Anti-Ad Trapping Mechanism
            from InstaAddict.core.resources import ResourceID""", fix_code)

# Then remove the later w, h assignment
text = text.replace("            w, h = d.info['displayWidth'], d.info['displayHeight']\n            \n            if is_valid_topic:", "            if is_valid_topic:")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

import re
with open('InstaAddict/plugins/interact_reels.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'logger.error(f"Reels Stalker Comment Error: {e}")',
    'import traceback\n                logger.error(f"Reels Stalker Comment Error: {e}\\n{traceback.format_exc()}")'
)

with open('InstaAddict/plugins/interact_reels.py', 'w', encoding='utf-8') as f:
    f.write(code)

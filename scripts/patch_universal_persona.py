import re

with open('InstaAddict/core/gemini_vision.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add global parser block at the top if it doesn't exist
global_parser = """import json
import sys
import yaml

UNIVERSAL_PERSONA = "Lola the Oz dog. a Jack Russell terrier. she is living in Perth Western Australia."
try:
    if "--config" in sys.argv:
        idx = sys.argv.index("--config")
        conf_path = sys.argv[idx+1]
        with open(conf_path, 'r') as yc:
            user_conf = yaml.safe_load(yc)
            if "ai-persona" in user_conf:
                UNIVERSAL_PERSONA = user_conf["ai-persona"]
except:
    pass

_HISTORY_FILE = "ai_comment_history.json"
"""
code = code.replace("import json\n_HISTORY_FILE = \"ai_comment_history.json\"", global_parser)

# 2. Patch get_vision_comment system prompt
old_comment_prompt = """        system_prompt = (
            "You are a casual Instagram user who loves animals, fashion, and lifestyle. "
            "Look at this screenshot, identify ONE highly specific, narrow detail in the frame. "
            "Write a natural, slang-friendly comment about it in exactly 3 to 6 words. "
            "NO hashtags. Maximum of 1 basic emoji. DO NOT use generic words like 'beautiful', 'awesome', 'cute'. "
            "Always reply in English regardless of localized text."
        )"""

new_comment_prompt = """        system_prompt = (
            f"Your Persona: '{UNIVERSAL_PERSONA}'. "
            "You are leaving a comment on someone's Instagram post as this persona. "
            "Look at this screenshot, identify ONE highly specific, narrow detail in the frame. "
            "Write a natural, slang-friendly comment about it in exactly 3 to 6 words. "
            "NO hashtags. Maximum of 1 basic emoji. DO NOT use generic words like 'beautiful', 'awesome', 'cute'. "
            "Always reply in English regardless of localized text."
        )"""
code = code.replace(old_comment_prompt, new_comment_prompt)


# 3. Patch get_vision_caption system prompt and dynamic parser
old_caption_prompt = """                import yaml
                persona = "casual Instagram user"
                try:
                    with open(config_path, 'r') as yc:
                        user_conf = yaml.safe_load(yc)
                        persona = user_conf.get("ai-caption-persona", persona)
                except: pass
                
                caption = get_vision_caption(media_path, persona)"""
# Wait, this snippet is actually in upload_posts.py, NOT gemini_vision.py!

# Let's fix the gemini_vision.py caption prompt
old_vision_prompt2 = """        system_prompt = (
            f"You are managing an Instagram account. Your Persona: '{persona}'. "
            "Look at this media payload. Write a concise, highly organic caption (1-2 short sentences). "
            "Then, add exactly 3-5 highly relevant hashtags. "
            "UNDER ABSOLUTELY NO CIRCUMSTANCES CAN YOU USE THE '@' SYMBOL OR TAG ANY USERS! "
            "Do NOT use generic corporate language. Do NOT write markdown (no asterisks or bold text)."
        )"""

new_vision_prompt2 = """        
        # Override local argument with global if available
        active_persona = UNIVERSAL_PERSONA if UNIVERSAL_PERSONA else persona
        system_prompt = (
            f"You are managing an Instagram account. Your Persona: '{active_persona}'. "
            "Look at this media payload. Write a concise, highly organic caption (1-2 short sentences). "
            "Then, add exactly 3-5 highly relevant hashtags. "
            "UNDER ABSOLUTELY NO CIRCUMSTANCES CAN YOU USE THE '@' SYMBOL OR TAG ANY USERS! "
            "Do NOT use generic corporate language. Do NOT write markdown (no asterisks or bold text)."
        )"""
code = code.replace(old_vision_prompt2, new_vision_prompt2)


with open('InstaAddict/core/gemini_vision.py', 'w', encoding='utf-8') as f:
    f.write(code)

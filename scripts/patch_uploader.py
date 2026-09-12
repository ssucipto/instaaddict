import re

with open('InstaAddict/plugins/upload_posts.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add AI Import
if "get_vision_caption" not in code:
    code = code.replace("from InstaAddict.core.utils import random_sleep", "from InstaAddict.core.utils import random_sleep\nfrom InstaAddict.core.gemini_vision import get_vision_caption")

old_fetch_loop = """
        json_files: List[str] = [f for f in os.listdir(pending_dir) if f.endswith('.json')]
        if not json_files:
            return

        for j_file in json_files:
             base_name: str = os.path.splitext(j_file)[0]
             json_path: str = os.path.join(pending_dir, j_file)
             
             media_files: List[str] = [
                 f for f in os.listdir(pending_dir) 
                 if f.startswith(base_name) and f.endswith(ALLOWED_EXTENSIONS)
             ]
             if not media_files:
                 logger.warning(f"No valid media ({ALLOWED_EXTENSIONS}) found for {base_name}.")
                 continue

             media_file: str = media_files[0]
             media_path: str = os.path.join(pending_dir, media_file)

             try:
                 with open(json_path, 'r', encoding='utf-8') as f:
                     data: Dict[str, Any] = json.load(f)
                     caption: str = data.get("caption", "")
             except (json.JSONDecodeError, IOError) as e:
                 logger.error(f"Malformed JSON payload in {j_file}: {e}")
                 continue

             logger.info(f"Uploading {media_file} with caption: {caption[:20]}...")
             
             success: bool = self._upload_to_ig(device, media_path, caption)

             if success:
                 logger.info(f"Successfully posted! Moving {base_name} to published queue.")
                 os.makedirs(published_dir, exist_ok=True)
                 os.rename(json_path, os.path.join(published_dir, j_file))
                 os.rename(media_path, os.path.join(published_dir, media_file))
             else:
                 logger.error(f"Failed to verify successful upload for {base_name}. Keeping in pending queue protecting asset.")
                 
             break"""

new_fetch_loop = """
        # M6: Autopilot Uploads (Media-First Architecture)
        all_files = os.listdir(pending_dir)
        media_files = [f for f in all_files if f.endswith(ALLOWED_EXTENSIONS)]
        
        if not media_files:
            return

        for media_file in media_files:
            base_name = os.path.splitext(media_file)[0]
            media_path = os.path.join(pending_dir, media_file)
            json_path = os.path.join(pending_dir, f"{base_name}.json")
            
            caption = ""
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        caption = data.get("caption", "")
                        logger.info(f"Human override caption found for {media_file}.")
                except Exception as e:
                    logger.error(f"Failed reading JSON override {json_path}: {e}")
            
            if not caption:
                logger.info(f"No caption provided for {media_file}. Engaging AI Autopilot Vision-Captioner...")
                import yaml
                persona = "casual Instagram user"
                try:
                    with open(config_path, 'r') as yc:
                        user_conf = yaml.safe_load(yc)
                        persona = user_conf.get("ai-caption-persona", persona)
                except: pass
                
                caption = get_vision_caption(media_path, persona)
            
            logger.info(f"Uploading {media_file} with AI/Human caption: {caption[:30]}...")
            success = self._upload_to_ig(device, media_path, caption)

            if success:
                logger.info(f"Successfully posted! Archiving payload.")
                os.makedirs(published_dir, exist_ok=True)
                os.rename(media_path, os.path.join(published_dir, media_file))
                if os.path.exists(json_path):
                    os.rename(json_path, os.path.join(published_dir, f"{base_name}.json"))
            else:
                logger.error(f"Upload failed for {media_file}. Queued for retry.")
            
            break"""

code = code.replace(old_fetch_loop, new_fetch_loop)

# Safety Fallback: Remove newlines from injected strings since it might prematurely POST or crash Android XML.
if "caption_box.set_text(caption)" in code:
    code = code.replace("caption_box.set_text(caption)", 'caption_box.set_text(caption.replace("\\n", "  "))')

with open('InstaAddict/plugins/upload_posts.py', 'w', encoding='utf-8') as f:
    f.write(code)

import re
with open('InstaAddict/core/gemini_vision.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_function = """

def get_vision_caption(media_path: str, persona: str = "casual Instagram user") -> str:
    global VISION_API_DEAD, SESSION_API_CALLS
    
    if VISION_API_DEAD:
        return ""
        
    if SESSION_API_CALLS >= MAX_API_CALLS_PER_SESSION:
        logger.warning("Gemini AI reached local safety limit of 50 calls. Severing VLM.")
        VISION_API_DEAD = True
        return ""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "INSERT_YOUR_KEY_HERE":
        logger.warning("No Gemini API key found in .env. Skipping Vision AI Captioner.")
        VISION_API_DEAD = True
        return ""
        
    SESSION_API_CALLS += 1
    genai.configure(api_key=api_key)
    
    try:
        mime = "video/mp4" if media_path.lower().endswith(('.mp4', '.mov')) else "image/jpeg"
        
        if "video" in mime:
            logger.info("Uploading video chunk to Gemini natively for captioning...")
            media_item = genai.upload_file(media_path, mime_type=mime)
        else:
            # Compress with Pillow (Ram-Only BytesIO) for fast upload
            img = Image.open(media_path)
            img = img.convert("RGB")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            media_item = img
        
        system_prompt = (
            f"You are managing an Instagram account. Your Persona: '{persona}'. "
            "Look at this media payload. Write a concise, highly organic caption (1-2 short sentences). "
            "Then, add exactly 3-5 highly relevant hashtags. "
            "UNDER ABSOLUTELY NO CIRCUMSTANCES CAN YOU USE THE '@' SYMBOL OR TAG ANY USERS! "
            "Do NOT use generic corporate language. Do NOT write markdown (no asterisks or bold text)."
        )

        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.9
            )
        )
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]
        
        logger.info("Executing Vision-AI Caption Generation...")
        response = model.generate_content(
            media_item,
            safety_settings=safety_settings,
            request_options={"timeout": 15.0} # Slightly longer timeout for video chunking
        )
        
        caption = response.text
        # Markdown & Spam Sanitizer
        caption = caption.replace("*", "").replace("@", "").strip()
        logger.info(f"AI Caption generated: {caption}")
        return caption
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gemini Vision Caption API Exception: {error_msg}")
        if "429" in error_msg or "401" in error_msg:
            logger.error("Circuit Breaker Activated. Disabling Vision AI for session.")
            VISION_API_DEAD = True
        return ""
"""
code = code + new_function

with open('InstaAddict/core/gemini_vision.py', 'w', encoding='utf-8') as f:
    f.write(code)

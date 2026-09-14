import os
import re
import io
import time
import logging
import json
import sys
import yaml
import warnings
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

VISION_API_DEAD = False
SESSION_API_CALLS = 0
MAX_API_CALLS_PER_SESSION = 400

UNIVERSAL_PERSONA = "Lola the Oz dog. a Jack Russell terrier. she is living in Perth Western Australia."
try:
    if "--config" in sys.argv:
        idx = sys.argv.index("--config")
        if idx + 1 < len(sys.argv):
            conf_path = sys.argv[idx + 1]
            if os.path.exists(conf_path):
                with open(conf_path, "r", encoding="utf-8") as yc:
                    user_conf = yaml.safe_load(yc) or {}
                    if "ai-persona" in user_conf:
                        UNIVERSAL_PERSONA = user_conf["ai-persona"]
except (IndexError, OSError, yaml.YAMLError) as e:
    logger.debug(f"Could not pre-load ai-persona from CLI config: {e}")



def _sanitize_response(text: str) -> str:
    """Regex block to prevent LLM outings like 'I cannot assist'."""
    forbidden = re.compile(
        r"(AI|language model|cannot assist|safety reasons|I'm an AI|As an AI|I can't|sorry)", 
        re.IGNORECASE
    )
    if forbidden.search(text):
        logger.warning(f"Gemini attempted to out itself. Blocking text: {text}")
        return ""
    
    text = text.replace('"', '').strip()
    return text

def get_vision_comment(device, _reserved: str = '') -> str:
    global VISION_API_DEAD, SESSION_API_CALLS
    
    if VISION_API_DEAD:
        return ""
        
    if SESSION_API_CALLS >= MAX_API_CALLS_PER_SESSION:
        logger.warning("Gemini AI reached local safety limit of 400 calls. Severing VLM.")
        VISION_API_DEAD = True
        return ""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "INSERT_YOUR_KEY_HERE":
        logger.warning("No Gemini API key found in .env. Skipping Vision AI.")
        VISION_API_DEAD = True
        return ""
        
    try:
        raw_screenshot = device.deviceV2.screenshot(format='raw')
    except Exception as e:
        logger.error(f"Failed to capture screen: {e}")
        return ""
        
    SESSION_API_CALLS += 1

    genai.configure(api_key=api_key)
    
    for attempt in range(3):
        try:
            # Compress with Pillow (Ram-Only BytesIO)
            img = Image.open(io.BytesIO(raw_screenshot))
            img = img.convert("RGB")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            system_prompt = (
                f"Your Persona: '{UNIVERSAL_PERSONA}'. "
                "You are leaving a comment on someone's Instagram post as this persona. "
                "Look at this screenshot, identify ONE highly specific, narrow detail in the frame. "
                "Write a natural, slang-friendly comment about it in exactly 3 to 6 words. "
                "NO hashtags. Maximum of 1 basic emoji. DO NOT use generic words like 'beautiful', 'awesome', 'cute'. "
                "Always reply in English regardless of localized text."
            )

            model = genai.GenerativeModel(
                model_name='gemini-3.7-flash',
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=150,
                    temperature=0.9
                )
            )
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ]
            
            response = model.generate_content(
                img,
                safety_settings=safety_settings,
                request_options={"timeout": 30.0}
            )
            
            try:
                comment = response.text
                return _sanitize_response(comment)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse response text (Safety blocked or empty): {e}")
                return ""
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini Vision API Exception: {error_msg}")
            if "401" in error_msg:
                logger.error("Circuit Breaker Activated (Invalid Auth). Disabling Vision AI for session.")
                VISION_API_DEAD = True
                break
            elif "429" in error_msg or "Quota exceeded" in error_msg:
                wait_time = 60
                import re
                m = re.search(r"retry in ([\d\.]+)s", error_msg)
                if not m:
                    m = re.search(r"seconds:\s*(\d+)", error_msg)
                if m:
                    wait_time = int(float(m.group(1))) + 5
                logger.warning(f"Rate Limit Hit. Sleeping for {wait_time}s before resuming (attempt {attempt+1}/3)...")
                import time
                time.sleep(wait_time)
                continue
            break
    return ""


def get_vision_caption(media_path: str, persona: str = "casual Instagram user") -> str:
    global VISION_API_DEAD, SESSION_API_CALLS
    
    if VISION_API_DEAD:
        return ""
        
    if SESSION_API_CALLS >= MAX_API_CALLS_PER_SESSION:
        logger.warning("Gemini AI reached local safety limit of 400 calls. Severing VLM.")
        VISION_API_DEAD = True
        return ""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "INSERT_YOUR_KEY_HERE":
        logger.warning("No Gemini API key found in .env. Skipping Vision AI Captioner.")
        VISION_API_DEAD = True
        return ""
        
    SESSION_API_CALLS += 1
    genai.configure(api_key=api_key)
    
    for attempt in range(3):
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
            
            
            # Override local argument with global if available
            active_persona = UNIVERSAL_PERSONA if UNIVERSAL_PERSONA else persona
            system_prompt = (
                f"You are managing an Instagram account. Your Persona: '{active_persona}'. "
                "Look at this media payload. Write a concise, highly organic caption (1-2 short sentences). "
                "Then, add exactly 3-5 highly relevant hashtags. "
                "UNDER ABSOLUTELY NO CIRCUMSTANCES CAN YOU USE THE '@' SYMBOL OR TAG ANY USERS! "
                "Do NOT use generic corporate language. Do NOT write markdown (no asterisks or bold text)."
            )

            model = genai.GenerativeModel(
                model_name='gemini-3.7-flash',
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
                request_options={"timeout": 60.0} # Sufficient timeout for video chunking
            )
            
            try:
                caption = response.text
                # Markdown & Spam Sanitizer
                caption = caption.replace("*", "").replace("@", "").strip()
                logger.info(f"AI Caption generated: {caption}")
                return caption
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse response text (Safety blocked or empty): {e}")
                return ""
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini Vision Caption API Exception: {error_msg}")
            if "401" in error_msg:
                logger.error("Circuit Breaker Activated (Invalid Auth). Disabling Vision AI for session.")
                VISION_API_DEAD = True
                break
            elif "429" in error_msg or "Quota exceeded" in error_msg:
                wait_time = 60
                import re
                m = re.search(r"retry in ([\d\.]+)s", error_msg)
                if not m:
                    m = re.search(r"seconds:\s*(\d+)", error_msg)
                if m:
                    wait_time = int(float(m.group(1))) + 5
                logger.warning(f"Rate Limit Hit. Sleeping for {wait_time}s before resuming (attempt {attempt+1}/3)...")
                import time
                time.sleep(wait_time)
                continue
            break
    return ""


def evaluate_and_comment_reel(img_bytes, topic="dogs or animals") -> str:
    """1-Shot VLM: Validates if a reel matches the topic AND generates a comment if true."""
    global VISION_API_DEAD, SESSION_API_CALLS
    if VISION_API_DEAD:
        return "" # Fallback

    if SESSION_API_CALLS >= MAX_API_CALLS_PER_SESSION:
        logger.warning("Gemini AI reached local safety limit of 400 calls. Severing VLM.")
        VISION_API_DEAD = True
        return ""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "INSERT_YOUR_KEY_HERE":
        logger.warning("No Gemini API key found in .env. Skipping Vision AI Filter.")
        VISION_API_DEAD = True
        return ""

    SESSION_API_CALLS += 1
    
    for attempt in range(3):
        try:
            genai.configure(api_key=api_key)
            
            img = Image.open(io.BytesIO(img_bytes))
            img = img.convert("RGB")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            prompt = (
                f"Your Persona: '{UNIVERSAL_PERSONA}'. "
                f"Look at this screenshot of an Instagram Reel. Is it predominantly about {topic}? "
                "If NO, reply strictly with the word: NO. "
                "If YES, write a natural, slang-friendly comment about a highly specific, narrow detail in exactly 3 to 6 words. "
                "NO hashtags. Maximum of 1 basic emoji. DO NOT use generic words like 'beautiful', 'awesome', 'cute'."
            )
            
            model = genai.GenerativeModel(
                model_name='gemini-3.7-flash',
                system_instruction=prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=150,
                    temperature=0.7
                )
            )
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ]
            
            response = model.generate_content(
                img,
                safety_settings=safety_settings,
                request_options={"timeout": 30.0}
            )
            
            try:
                answer = response.text.strip()
                if answer.upper() == "NO":
                    return ""
                return _sanitize_response(answer)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse response text (Safety blocked or empty): {e}")
                return ""
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Reel Vision Evaluation Failed: {error_msg}")
            if "401" in error_msg:
                logger.error("Circuit Breaker Activated (Invalid Auth). Disabling Vision AI for session.")
                VISION_API_DEAD = True
                break
            elif "429" in error_msg or "Quota exceeded" in error_msg:
                wait_time = 60
                import re
                m = re.search(r"retry in ([\d\.]+)s", error_msg)
                if not m:
                    m = re.search(r"seconds:\s*(\d+)", error_msg)
                if m:
                    wait_time = int(float(m.group(1))) + 5
                logger.warning(f"Rate Limit Hit. Sleeping for {wait_time}s before resuming (attempt {attempt+1}/3)...")
                import time
                time.sleep(wait_time)
                continue
            break
    return ""

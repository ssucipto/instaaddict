import os
import re
import io
import logging
from PIL import Image
import warnings
warnings.simplefilter("ignore")
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

VISION_API_DEAD = False
SESSION_API_CALLS = 0
MAX_API_CALLS_PER_SESSION = 50

import json
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

_RECENT_INTERACTIONS = set()

if os.path.exists(_HISTORY_FILE):
    try:
        with open(_HISTORY_FILE, "r") as f:
            _RECENT_INTERACTIONS = set(json.load(f))
    except:
        pass

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
        logger.warning("Gemini AI reached local safety limit of 50 calls. Severing VLM.")
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
        
    import hashlib
    screen_hash = hashlib.md5(raw_screenshot[:1024]).hexdigest()

    if screen_hash in _RECENT_INTERACTIONS:
        logger.warning(f"Idempotency Guard: Already commented on optical hash {screen_hash}. Skipping.")
        return ""

    SESSION_API_CALLS += 1
    _RECENT_INTERACTIONS.add(screen_hash)
    try:
        with open(_HISTORY_FILE, "w") as f:
            json.dump(list(_RECENT_INTERACTIONS), f)
    except:
        pass
    
    genai.configure(api_key=api_key)
    
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
            model_name='gemini-1.5-flash',
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=15,
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
            request_options={"timeout": 5.0}
        )
        
        comment = response.text
        return _sanitize_response(comment)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gemini Vision API Exception: {error_msg}")
        if "429" in error_msg or "401" in error_msg:
            logger.error("Circuit Breaker Activated. Disabling Vision AI for session.")
            VISION_API_DEAD = True
        return ""


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
i m p o r t   o s  
 i m p o r t   r e  
 i m p o r t   i o  
 i m p o r t   l o g g i n g  
 f r o m   P I L   i m p o r t   I m a g e  
 i m p o r t   w a r n i n g s  
 w a r n i n g s . s i m p l e f i l t e r ( " i g n o r e " )  
 i m p o r t   g o o g l e . g e n e r a t i v e a i   a s   g e n a i  
  
 l o g g e r   =   l o g g i n g . g e t L o g g e r ( _ _ n a m e _ _ )  
  
 d e f   e v a l u a t e _ r e e l _ c o n t e n t ( i m g _ b y t e s ,   t o p i c = " d o g s   o r   a n i m a l s " ) :  
         " " " V a l i d a t e s   i f   a   r e e l   m a t c h e s   t h e   t a r g e t   t a x o n o m y   t o   t r a i n   t h e   a l g o r i t h m . " " "  
         g l o b a l   V I S I O N _ A P I _ D E A D  
         i f   V I S I O N _ A P I _ D E A D :  
                 r e t u r n   T r u e   #   F a l l b a c k  
  
         t r y :  
                 g e n a i . c o n f i g u r e ( a p i _ k e y = o s . e n v i r o n . g e t ( " G E M I N I _ A P I _ K E Y " ) )  
                 m o d e l   =   g e n a i . G e n e r a t i v e M o d e l ( ' g e m i n i - 1 . 5 - f l a s h ' )  
                  
                 i m g   =   I m a g e . o p e n ( i o . B y t e s I O ( i m g _ b y t e s ) )  
                  
                 p r o m p t   =   f " L o o k   a t   t h i s   s c r e e n s h o t   o f   a n   I n s t a g r a m   R e e l .   D o e s   t h i s   i m a g e   p r e d o m i n a n t l y   f e a t u r e   { t o p i c } ?   R e p l y   s t r i c t l y   w i t h   a   s i n g l e   w o r d :   Y E S   o r   N O . "  
                  
                 r e s p o n s e   =   m o d e l . g e n e r a t e _ c o n t e n t (  
                         [ p r o m p t ,   i m g ] ,  
                         g e n e r a t i o n _ c o n f i g = g e n a i . G e n e r a t i o n C o n f i g (  
                                 t e m p e r a t u r e = 0 . 0 ,  
                                 m a x _ o u t p u t _ t o k e n s = 1 0 ,  
                         )  
                 )  
                  
                 a n s w e r   =   r e s p o n s e . t e x t . s t r i p ( ) . u p p e r ( )  
                 i f   " Y E S "   i n   a n s w e r :  
                         r e t u r n   T r u e  
                 r e t u r n   F a l s e  
         e x c e p t   E x c e p t i o n   a s   e :  
                 l o g g e r . e r r o r ( f " R e e l   V i s i o n   E v a l u a t i o n   F a i l e d :   { e } " )  
                 r e t u r n   T r u e   #   D e f a u l t   t o   o p e n   o n   f a i l u r e  
 
import os
import re
import io
import logging
from PIL import Image
import warnings
warnings.simplefilter("ignore")
import google.generativeai as genai

logger = logging.getLogger(__name__)

def evaluate_reel_content(img_bytes, topic="dogs or animals"):
    """Validates if a reel matches the target taxonomy to train the algorithm."""
    global VISION_API_DEAD
    if VISION_API_DEAD:
        return True # Fallback

    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        img = Image.open(io.BytesIO(img_bytes))
        
        prompt = f"Look at this screenshot of an Instagram Reel. Does this image predominantly feature {topic}? Reply strictly with a single word: YES or NO."
        
        response = model.generate_content(
            [prompt, img],
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=10,
            )
        )
        
        answer = response.text.strip().upper()
        if "YES" in answer:
            return True
        return False
    except Exception as e:
        logger.error(f"Reel Vision Evaluation Failed: {e}")
        return True # Default to open on failure

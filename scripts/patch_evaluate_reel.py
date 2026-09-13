import os
import re

file_path = 'InstaAddict/core/gemini_vision.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace evaluate_reel_content method entirely
old_func = r'def evaluate_reel_content\(img_bytes, topic="dogs or animals"\):[\s\S]*?return True # Default to open on failure'
new_func = """def evaluate_reel_content(img_bytes, topic="dogs or animals"):
    \"\"\"Validates if a reel matches the target taxonomy to train the algorithm.\"\"\"
    global VISION_API_DEAD, SESSION_API_CALLS
    if VISION_API_DEAD:
        return True # Fallback

    if SESSION_API_CALLS >= MAX_API_CALLS_PER_SESSION:
        logger.warning("Gemini AI reached local safety limit of 50 calls. Severing VLM.")
        VISION_API_DEAD = True
        return True

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "INSERT_YOUR_KEY_HERE":
        logger.warning("No Gemini API key found in .env. Skipping Vision AI Filter.")
        VISION_API_DEAD = True
        return True

    SESSION_API_CALLS += 1
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Local import to avoid top level issues if any
        import io
        from PIL import Image
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
        return True"""

text = re.sub(old_func, new_func, text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

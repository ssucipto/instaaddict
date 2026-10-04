import os
import re
import io
import time
import random
import logging
import sys
import yaml
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

VISION_API_DEAD = False
SESSION_API_CALLS = 0
MAX_API_CALLS_PER_SESSION = 400

UNIVERSAL_PERSONA = (
    "A friendly and engaging Instagram creator sharing daily life moments, adventures, and insights."
)

def _track_vision():
    try:
        from InstaAddict.core.telemetry import PerformanceTracker
        return PerformanceTracker.get_instance().measure("api", "gemini_vision")
    except Exception:
        from contextlib import nullcontext
        return nullcontext()

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



def get_active_persona(override: str = None) -> str:
    """Resolve active AI persona dynamically with CLI config and override fallback."""
    if override and str(override).strip():
        return str(override).strip()
    global UNIVERSAL_PERSONA
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
        logger.debug(f"Could not refresh ai-persona from CLI config: {e}")
    return UNIVERSAL_PERSONA


def _sanitize_response(text: str) -> str:
    """Sanitizes LLM outputs: strips hidden zero-width Unicode/ZWJ characters, skin tones, em-dashes, and AI outings."""
    if not text:
        return ""
    # Strip zero-width and invisible control characters (ZWJ U+200D, ZWSP U+200B, BOM U+FEFF, soft hyphen, bidi overrides)
    text = re.sub(r"[\u200B-\u200D\uFEFF\u00AD\u200E\u200F\u202A-\u202E\u2066-\u2069]", "", text)
    # Strip emoji skin-tone modifiers (U+1F3FB - U+1F3FF) to avoid compound mojibake on Android IME
    text = re.sub(r"[\U0001F3FB-\U0001F3FF]", "", text)

    # Sanitize em-dashes (U+2014) and en-dashes (U+2013) to prevent dead-giveaway AI punctuation
    text = text.replace("—", ", ").replace("–", "- ")
    # Clean up double punctuation or awkward spacing created by dash replacement
    text = re.sub(r"\s*,\s*,+", ",", text)
    text = re.sub(r"\s+", " ", text)

    forbidden = re.compile(
        r"(AI|language model|cannot assist|safety reasons|I'm an AI|As an AI|I can't|sorry|as an artificial)", 
        re.IGNORECASE
    )
    if forbidden.search(text):
        logger.warning(f"Gemini attempted to out itself. Blocking text: {text}")
        return ""
    
    text = text.replace('"', '').strip()
    return text


def _safe_extract_text(response, default: str = "") -> str:
    """Safely extracts text from Gemini response without throwing on safety blocks or empty candidates."""
    if not response:
        return default
    try:
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)
            if str(finish_reason) in ("2", "FinishReason.SAFETY", "SAFETY"):
                logger.warning("Gemini Vision response blocked by safety filter (finish_reason=2).")
                return default
        return response.text
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse response text (Safety blocked or empty): {e}")
        return default


def _safe_rate_limit_sleep(
    wait_time: int, attempt: int, max_retries: int, context: str = "Vision AI"
) -> None:
    """Sleeps safely during API rate limits without triggering BotWatchdog inactivity timeouts."""
    logger.warning(
        f"Rate Limit Hit ({context}). Sleeping for {wait_time}s before resuming (attempt {attempt + 1}/{max_retries})..."
    )
    watchdog = None
    try:
        from InstaAddict.core.watchdog import BotWatchdog

        watchdog = BotWatchdog.get_instance()
        watchdog.pause()
    except Exception:
        pass

    try:
        remaining = wait_time
        while remaining > 0:
            chunk = min(5, remaining)
            time.sleep(chunk)
            remaining -= chunk
            try:
                from InstaAddict.core.watchdog import record_heartbeat

                record_heartbeat(
                    "gemini_vision",
                    f"Rate limit backoff ({wait_time - remaining}/{wait_time}s)",
                )
            except Exception:
                pass
    finally:
        if watchdog:
            try:
                watchdog.resume()
            except Exception:
                pass

SENTIMENT_SYMPATHETIC = "SYMPATHETIC"
SENTIMENT_CELEBRATORY = "CELEBRATORY"
SENTIMENT_PLAYFUL = "PLAYFUL"
SENTIMENT_INQUISITIVE = "INQUISITIVE"
SENTIMENT_APPRECIATIVE = "APPRECIATIVE"


def classify_sentiment(caption: str = "", text_context: str = "") -> str:
    """Classifies the emotional tone and context of a post to ensure comments are empathetic, celebratory, or appropriate."""
    combined = f"{caption} {text_context}".lower()

    sympathetic_keywords = [
        "rainbow bridge", "passed away", "rip", "rest in peace", "rest easy", "cross the bridge",
        "broken heart", "heartbroken", "goodbye", "miss you so much", "forever in our hearts",
        "vet", "surgery", "hospital", "sick", "illness", "injury", "cancer", "tumor", "pain",
        "emergency", "pray for", "healing thoughts", "prayers", "fight", "struggling"
    ]
    for kw in sympathetic_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", combined):
            return SENTIMENT_SYMPATHETIC

    celebratory_keywords = [
        "birthday", "happy birthday", "bday", "gotcha day", "gotchaday", "adoptiversary", "anniversary",
        "milestone", "graduate", "graduated", "celebrate", "celebrating", "first year",
        "turned 1", "turned 2", "turned 3", "turned 4", "turned 5", "years old", "congrats",
        "congratulations", "winner", "we won", "champion"
    ]
    for kw in celebratory_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", combined):
            return SENTIMENT_CELEBRATORY

    playful_keywords = [
        "zoomies", "derp", "silly", "chaos", "mischief", "trouble", "funny", "goofy",
        "stole", "caught red handed", "guilty", "crazy", "comedy", "gremlin", "dork",
        "clown", "monster", "shark", "bork", "heck", "drama queen", "tantrum"
    ]
    for kw in playful_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", combined):
            return SENTIMENT_PLAYFUL

    inquisitive_keywords = [
        "recommend", "recommendations", "advice", "what do you think", "thoughts?",
        "suggestions", "any tips", "help me choose", "which one", "who else", "anyone else"
    ]
    if "?" in combined or any(re.search(r"\b" + re.escape(kw) + r"\b", combined) for kw in inquisitive_keywords):
        return SENTIMENT_INQUISITIVE

    return SENTIMENT_APPRECIATIVE


FALLBACK_COMMENTS_BY_SENTIMENT = {
    SENTIMENT_SYMPATHETIC: [
        "Sending so much love and gentle thoughts your way right now.",
        "Holding you and your sweet fur baby close in our hearts today.",
        "So incredibly sorry for your loss, sending the biggest hug your way.",
        "Thinking of you heaps during this heartbreaking time. Run free sweet angel.",
        "Sending healing strength and gentle cuddles for a speedy recovery mate.",
        "My heart aches for you. Take all the time you need, sending so much love.",
        "What a beautiful soul who brought so much pure joy. So sorry for your heartache.",
        "Crossing the rainbow bridge surrounded by so much endless love.",
        "Sending you all our warmth and love today, thinking of you guys.",
        "Wrapping you in gentle hugs and praying for a smooth recovery.",
        "So sorry you're going through this rough patch, sending nothing but love.",
        "Such heartbreaking news, they were truly one of a kind and so cherished.",
        "Rest easy sweet one, you gave them the most incredible life full of love.",
        "Sending massive healing vibes and positive energy your way today.",
        "Heartbroken for your family mate, take the gentlest care of yourself.",
        "Thinking of you so much today, sending heartfelt cuddles and comfort.",
        "Forever loved and never forgotten. Sending deepest condolences.",
        "Hoping each day brings a little bit more comfort and healing your way.",
        "Sending quiet love and warm prayers to your whole crew right now.",
        "So sorry mate, words can't capture it. Sending all our heartfelt love.",
        "Holding you in our thoughts through this difficult time.",
    ],
    SENTIMENT_CELEBRATORY: [
        "Happiest birthday to an absolute legend! Hope the treats are flowing today.",
        "Happy gotcha day mate! What a wonderful story and a lucky pup.",
        "Cheers to another fantastic year full of adventures and endless tail wags.",
        "Huge congratulations on this milestone! Absolutely stoked for you guys.",
        "Look at that proud face! Hope you get spoiled with extra belly rubs today.",
        "Happy birthday handsome! May your day be packed with toys and sunshine.",
        "What a ripper milestone, wishing you many more wonderful years together.",
        "Happy adoptiversary! Best decision ever made, look at that pure happiness.",
        "Huge cheers to celebrating such an awesome milestone with the best crew.",
        "Happy birthday gorgeous soul! Time for all the peanut butter treats.",
        "Celebrating you today mate, you bring so much sunshine into everyone's feed.",
        "So stoked to see this, happy gotcha day to the sweetest angel.",
        "A massive celebration well deserved! Sending all the party love.",
        "Look at that glowing birthday star! Hope you're showered in warm cuddles.",
        "Happy anniversary of finding each other, truly meant to be together.",
        "The biggest happy birthday mate, here's to many more ripper adventures.",
        "Celebrating another year of unconditional love and pure muddy happiness.",
        "Couldn't love this milestone more, hope the celebrations are huge today.",
        "Happy birthday sweetheart! Extra biscuits on the menu for sure.",
        "What a gorgeous journey to celebrate, wishing you the happiest day.",
    ],
    SENTIMENT_PLAYFUL: [
        "That face says zero regrets about whatever just went down here.",
        "Peak zoomies energy right there, absolutely love to see it.",
        "The pure chaos in those eyes is unmatched, what a little character.",
        "Caught right in the act and completely unbothered by it all.",
        "Definite guilty look going on, reckon they're definitely planning round two.",
        "That cheeky grin is cracking me up heaps, absolute comedy gold.",
        "Living life on fast forward right there, pure joy and wild speed.",
        "Someone woke up and chose complete chaos today, love every second of it.",
        "Not a single thought behind those adorable eyes except maximum fun.",
        "That innocent pose isn't fooling anyone mate, total mischief maker.",
        "Reckon they just set a new household land speed record right there.",
        "The dramatic flair here is Oscar worthy, give this legend an award.",
        "Certified goofball doing what they do best, never change mate.",
        "That little side eye says everything we need to know about what happened.",
        "Pure comedy in one snap, this absolutely made my whole morning.",
        "Looking very pleased with their handiwork, no remorse whatsoever.",
        "The sass is totally off the charts today, absolute ripper personality.",
        "That look of determination right before the zoomies kick into high gear.",
        "Can never stay mad at that face no matter the chaos caused.",
        "An absolute menace in the sweetest possible way, pure gold.",
    ],
    SENTIMENT_INQUISITIVE: [
        "Reckon option one looks like a winner, but honestly both are brilliant.",
        "We had similar luck with gentle puzzle toys, really keeps them happily busy.",
        "Definitely leaning towards the first one mate, suits the vibe perfectly.",
        "Always love hearing how others handle this, keen to see what you choose.",
        "Hands down the second choice for me, looks heaps more comfortable.",
        "Such a great question! We found sticking to routine made all the difference.",
        "Hard to pick when both look so good, but the left one catches my eye.",
        "Been wondering the exact same thing lately, thanks for asking the room.",
        "Both are awesome but that first colourway really pops against the coat.",
        "Reckon you can't go wrong either way, depends on the adventure planned.",
        "My vote is firmly on option number one, classic and super practical.",
        "Such a tough call mate, but that second one looks built to last.",
        "We tried something similar last month and it was an absolute game changer.",
        "Always keen to see the community's thoughts on this, really good topic.",
        "I'd definitely go with the first option, looks spot on for daily walks.",
        "Curious how that one holds up in wet weather, looks really sturdy though.",
        "Team number one all the way, looks so comfy and well fitted.",
        "Both look top tier, but the second one has such a cool clean aesthetic.",
        "Great question mate, keen to hear what ends up working best for you.",
        "Voting for the first one here, looks totally effortless and fun.",
    ],
    SENTIMENT_APPRECIATIVE: [
        "Those soulful eyes are just melting my heart right now, so gorgeous.",
        "Such a peaceful moment captured here, soaking up the sweet sunshine.",
        "Look at that lovely coat glowing in the afternoon light, absolutely stunning.",
        "Living their absolute best life right here, couldn't look happier.",
        "That sweet gentle face is pure therapy for the feed today.",
        "Nothing beats cozy moments like this, enjoy every single second of it.",
        "What a gorgeous spot for an adventure, taking in all the fresh sniffs.",
        "Such a handsome pup right there, standing tall and looking so proud.",
        "That contented smile says it all, someone is definitely having a ripper day.",
        "The sweetest companion ever, that bond between you is so clearly special.",
        "So much warmth in this picture mate, really put a smile on my face.",
        "Just radiating pure calm and happiness today, absolutely love this shot.",
        "Those ears are out of this world adorable, what an angel.",
        "A proper little adventurer right there, ready to take on the world.",
        "Looking so relaxed and comfy, that's the weekend mood we all need.",
        "That sweet little nose is just begging for a gentle boop.",
        "Such an expressive face, you can just tell how loved this good boy is.",
        "The light hits so beautifully here, really gorgeous capture of your mate.",
        "Every single photo of this sweet soul just brightens up the day heaps.",
        "So much effortless charm, definitely deserves an extra treat today.",
        "The sweetest Sunday morning vibes right here, look at that relaxation.",
        "That happy tail wag is basically coming right through the screen.",
        "Looking so healthy and vibrant, what a true credit to your care.",
        "Just perfection in one photo, soak in all those wonderful cuddles.",
        "Pure gentle soul right there, thanks for sharing this sweet moment.",
    ],
}


def generate_sentiment_fallback(
    sentiment: str = SENTIMENT_APPRECIATIVE,
    author: str = "",
    memory=None,
) -> str:
    """Generates a contextual, non-repetitive fallback comment based on sentiment and past comment memory."""
    bucket = FALLBACK_COMMENTS_BY_SENTIMENT.get(
        sentiment, FALLBACK_COMMENTS_BY_SENTIMENT[SENTIMENT_APPRECIATIVE]
    )
    shuffled = list(bucket)
    random.shuffle(shuffled)

    for candidate in shuffled:
        if memory is not None and hasattr(memory, "is_similar_to_recent"):
            if memory.is_similar_to_recent(candidate, threshold=0.55):
                continue
        return candidate

    return random.choice(bucket)


def get_vision_comment(
    device,
    _reserved: str = '',
    caption: str = '',
    author: str = '',
    community_comments: list = None,
    media_type: str = 'photo',
    account_name: str = None,
) -> str:
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
        raw_screenshot = None
        if hasattr(device, "take_screenshot"):
            try:
                res = device.take_screenshot(format="raw")
                if isinstance(res, (bytes, bytearray)):
                    raw_screenshot = res
            except Exception:
                pass
        if raw_screenshot is None:
            if hasattr(device, "deviceV2") and hasattr(device.deviceV2, "screenshot"):
                try:
                    res = device.deviceV2.screenshot(format="raw")
                    if isinstance(res, (bytes, bytearray)):
                        raw_screenshot = res
                except Exception:
                    pass
        if raw_screenshot is None:
            raw_screenshot = b""
    except Exception as e:
        logger.error(f"Failed to capture screen: {e}")
        return ""

    if not raw_screenshot or (
        isinstance(raw_screenshot, (bytes, bytearray))
        and not (raw_screenshot.startswith(b"\x89PNG") or raw_screenshot.startswith(b"\xff\xd8\xff"))
    ):
        logger.warning(
            f"Screen capture buffer invalid ({len(raw_screenshot) if raw_screenshot else 0} bytes). Skipping Vision AI comment."
        )
        return ""
        
    SESSION_API_CALLS += 1

    genai.configure(api_key=api_key)
    
    memory = None
    try:
        from InstaAddict.core.storage import CommentMemory
        memory = CommentMemory.get_instance(account_name)
    except Exception:
        pass

    sentiment = classify_sentiment(caption)

    for attempt in range(3):
        try:
            # Compress with Pillow (Ram-Only BytesIO)
            img = Image.open(io.BytesIO(raw_screenshot))
            img = img.convert("RGB")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            active_persona = get_active_persona()

            sentiment_guidance = ""
            if sentiment == SENTIMENT_SYMPATHETIC:
                sentiment_guidance = (
                    "CRITICAL: The author is sharing grief, loss, illness, surgery, or sadness. "
                    "Respond with deep empathy, warmth, gentle sympathy, and heartfelt care. "
                    "NEVER make jokes, NEVER be cheerful or slangy, NEVER mention partying or fun."
                )
            elif sentiment == SENTIMENT_CELEBRATORY:
                sentiment_guidance = (
                    "The author is celebrating a milestone, birthday, gotcha day, or joyful event. "
                    "Express warm congratulations, excitement, and celebration."
                )
            elif sentiment == SENTIMENT_PLAYFUL:
                sentiment_guidance = (
                    "The post is playful, funny, showing zoomies or mischief. "
                    "Respond with humorous, witty, affectionate observations."
                )
            elif sentiment == SENTIMENT_INQUISITIVE:
                sentiment_guidance = (
                    "The author asked a question or asked for advice. "
                    "Provide a thoughtful, helpful, and friendly reaction or opinion."
                )
            else:
                sentiment_guidance = (
                    "The post shows a sweet, peaceful, or everyday moment. "
                    "Offer genuine, specific appreciation of a narrow detail."
                )

            author_clause = f"Author handle: @{author}\n" if author else ""
            caption_clause = f"Post caption: '{caption.strip()}'\n" if caption and caption.strip() else ""
            community_clause = ""
            if community_comments and isinstance(community_comments, list):
                clean_comms = [c.strip() for c in community_comments if c and c.strip()]
                if clean_comms:
                    community_clause = f"Existing comments in thread: {clean_comms[:3]}\nMake your comment distinct from these.\n"

            system_prompt = (
                f"Your Persona: '{active_persona}'. "
                "You are leaving a comment on someone's Instagram post as this persona. "
                f"{author_clause}"
                f"{caption_clause}"
                f"{community_clause}"
                f"{sentiment_guidance} "
                "Look at the screenshot and caption, identify ONE specific detail. "
                "Write a natural, conversational comment in 6 to 18 words. "
                "NO hashtags. Maximum of 1 basic emoji. DO NOT use generic words like 'beautiful', 'awesome', 'cute'. "
                "NEVER use em-dashes (— or –). NEVER sound like an AI assistant or bot. "
                "Speak naturally and casually with a slight, subtle Aussie flavour (e.g. subtle phrasing like 'reckon', 'heaps', 'ripper', 'mate', 'cheers', 'keen', but keep it subtle and tone-appropriate). "
                "Always reply in English regardless of localized text."
            )

            model = genai.GenerativeModel(
                model_name='gemini-3.6-flash',
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
            
            with _track_vision():
                response = model.generate_content(
                    img,
                    safety_settings=safety_settings,
                    request_options={"timeout": 30.0}
                )
            
            comment = _safe_extract_text(response)
            # CO-112: If response was blocked by safety filter on image, attempt text-only recovery
            if not comment and (caption or author):
                try:
                    logger.info("Attempting text-only recovery pass for comment...")
                    text_prompt = (
                        f"Post by @{author}: '{caption}'. "
                        f"{sentiment_guidance} "
                        "Write a natural, supportive comment in 6 to 18 words. No hashtags."
                    )
                    text_resp = model.generate_content(
                        text_prompt,
                        safety_settings=safety_settings,
                        request_options={"timeout": 15.0}
                    )
                    comment = _safe_extract_text(text_resp)
                except Exception as te:
                    logger.debug(f"Text-only recovery failed: {te}")

            if not comment:
                return ""

            cleaned = _sanitize_response(comment)
            if not cleaned:
                return ""

            # CO-116: Check against CommentMemory to avoid repetition
            if memory is not None and hasattr(memory, "is_similar_to_recent"):
                if memory.is_similar_to_recent(cleaned, threshold=0.55):
                    logger.info(
                        f"Comment '{cleaned}' is too similar to recent comments. Using novel sentiment fallback."
                    )
                    cleaned = generate_sentiment_fallback(
                        sentiment=sentiment, author=author, memory=memory
                    )

            if memory is not None and hasattr(memory, "add_comment") and cleaned:
                memory.add_comment(
                    cleaned,
                    target_username=author,
                    sentiment=sentiment,
                    post_type=media_type,
                )

            return cleaned
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini Vision API Exception: {error_msg}")
            if "429" in error_msg or "Quota exceeded" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if re.search(r"GenerateRequestsPerDay|daily|limit:\s*20\b", error_msg, re.IGNORECASE):
                    logger.warning(
                        "Daily Gemini Vision free-tier quota exhausted. Tripping circuit breaker for session."
                    )
                    VISION_API_DEAD = True
                    break
                wait_time = 60
                m = re.search(r"retry in ([\d\.]+)s", error_msg)
                if not m:
                    m = re.search(r"seconds:\s*(\d+)", error_msg)
                if m:
                    wait_time = int(float(m.group(1))) + 5
                _safe_rate_limit_sleep(wait_time, attempt, 3, context="Post Comment")
                continue
            elif re.search(r"\b401\b", error_msg) or "UNAUTHENTICATED" in error_msg or "API_KEY_INVALID" in error_msg:
                logger.error("Circuit Breaker Activated (Invalid Auth). Disabling Vision AI for session.")
                VISION_API_DEAD = True
                break
            break
    return ""



def get_vision_caption(
    media_path: str,
    persona: str = "casual Instagram user",
    user_context: str = "",
) -> str:
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
    
    max_retries = 5
    for attempt in range(max_retries):
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

            context_clause = ""
            if user_context and str(user_context).strip():
                context_clause = (
                    f" The user provided this contextual guidance / draft notes about the post: '{user_context.strip()}'. "
                    "Incorporate and extend these notes naturally based on what you visually observe in the media. "
                    "Blend the user's intent smoothly into your persona's authentic voice."
                )

            # Randomized engagement hook — one of 3 styles (CO-026 / F-10)
            _hook_style = random.randint(1, 3)
            if _hook_style == 1:
                hook_instruction = (
                    "End your caption with a short, open-ended question about the subject "
                    "that invites followers to share their thoughts or experiences."
                )
            elif _hook_style == 2:
                hook_instruction = (
                    "End your caption with a warm community invitation "
                    "(e.g. 'who else loves this?', 'drop your faves below 🐾') "
                    "that makes followers want to comment."
                )
            else:
                hook_instruction = (
                    "End your caption by calling out one specific detail from the scene "
                    "and add one fitting emoji reaction prompt to spark comments."
                )

            system_prompt = (
                f"You are managing an Instagram account. Your Persona: '{active_persona}'. "
                "Look at this media payload."
                f"{context_clause} "
                "Write a concise, highly organic caption (1-2 short sentences). "
                f"{hook_instruction} "
                "Then, add exactly 3-5 highly relevant hashtags. "
                "UNDER ABSOLUTELY NO CIRCUMSTANCES CAN YOU USE THE '@' SYMBOL OR TAG ANY USERS! "
                "Do NOT use generic corporate language. Do NOT write markdown (no asterisks or bold text). "
                "NEVER use em-dashes (— or –). Write with an authentic human voice with a slight, natural Aussie flavour."
            )

            model = genai.GenerativeModel(
                model_name='gemini-3.6-flash',
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.9,
                    max_output_tokens=300,  # Cap prevents Instagram 2200-char overflow (CO-026 / F-15)
                )
            )
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ]
            
            logger.info(f"Executing Vision-AI Caption Generation (attempt {attempt + 1}/{max_retries})...")
            with _track_vision():
                response = model.generate_content(
                    media_item,
                    safety_settings=safety_settings,
                    request_options={"timeout": 60.0} # Sufficient timeout for video chunking
                )
            
            caption = _safe_extract_text(response)
            if not caption:
                if attempt < max_retries - 1:
                    logger.warning(f"Vision AI returned empty caption (attempt {attempt + 1}/{max_retries}). Retrying after 2s...")
                    time.sleep(2)
                    continue
                return ""
            # Markdown, User Mentions & Unicode Sanitizer
            caption = caption.replace("*", "").replace("@", "")
            caption = _sanitize_response(caption)
            logger.info(f"AI Caption generated: {caption}")
            return caption
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini Vision Caption API Exception (attempt {attempt + 1}/{max_retries}): {error_msg}")
            if "429" in error_msg or "Quota exceeded" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if re.search(r"GenerateRequestsPerDay|daily|limit:\s*20\b", error_msg, re.IGNORECASE):
                    logger.warning(
                        "Daily Gemini Vision free-tier quota exhausted. Tripping circuit breaker for session."
                    )
                    VISION_API_DEAD = True
                    break
                wait_time = 30
                m = re.search(r"retry in ([\d\.]+)s", error_msg)
                if not m:
                    m = re.search(r"seconds:\s*(\d+)", error_msg)
                if m:
                    wait_time = int(float(m.group(1))) + 2
                _safe_rate_limit_sleep(wait_time, attempt, max_retries, context="Caption Gen")
                continue
            elif re.search(r"\b401\b", error_msg) or "UNAUTHENTICATED" in error_msg or "API_KEY_INVALID" in error_msg:
                logger.error("Circuit Breaker Activated (Invalid Auth). Disabling Vision AI for session.")
                VISION_API_DEAD = True
                break
            else:
                # Short interval retry for transient errors (504, 503, connection drops, etc.)
                if attempt < max_retries - 1:
                    short_delay = 2 * (attempt + 1)
                    logger.warning(f"Transient error encountered. Retrying in {short_delay}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(short_delay)
                    continue
            break
    return ""


def evaluate_and_comment_reel(
    img_bytes,
    topic="dogs or animals",
    caption: str = '',
    author: str = '',
    community_comments: list = None,
    account_name: str = None,
) -> str:
    """1-Shot VLM: Validates if a reel matches the topic AND generates a context-aware comment if true."""
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

    if not img_bytes or (
        isinstance(img_bytes, (bytes, bytearray))
        and not (img_bytes.startswith(b"\x89PNG") or img_bytes.startswith(b"\xff\xd8\xff"))
    ):
        logger.warning(
            f"Reel screenshot buffer invalid ({len(img_bytes) if img_bytes else 0} bytes). Skipping Vision AI evaluation."
        )
        return ""

    SESSION_API_CALLS += 1

    memory = None
    try:
        from InstaAddict.core.storage import CommentMemory
        memory = CommentMemory.get_instance(account_name)
    except Exception:
        pass

    sentiment = classify_sentiment(caption)

    for attempt in range(3):
        try:
            genai.configure(api_key=api_key)
            
            img = Image.open(io.BytesIO(img_bytes))
            img = img.convert("RGB")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            active_persona = get_active_persona()

            sentiment_guidance = ""
            if sentiment == SENTIMENT_SYMPATHETIC:
                sentiment_guidance = (
                    "CRITICAL: If the reel/caption expresses sadness, illness, or loss, "
                    "comment with gentle sympathy and love. NEVER make jokes or use upbeat slang."
                )
            elif sentiment == SENTIMENT_CELEBRATORY:
                sentiment_guidance = (
                    "The creator is celebrating a milestone or birthday. Express warm excitement and celebration."
                )
            elif sentiment == SENTIMENT_PLAYFUL:
                sentiment_guidance = (
                    "The reel shows playful antics, mischief, or zoomies. Respond with humorous, witty affection."
                )
            elif sentiment == SENTIMENT_INQUISITIVE:
                sentiment_guidance = (
                    "The creator asked a question or invited thoughts. Provide a friendly and engaging answer."
                )
            else:
                sentiment_guidance = (
                    "Offer genuine, specific appreciation of a visual detail in the reel."
                )

            author_clause = f"Creator: @{author}\n" if author else ""
            caption_clause = f"Reel caption: '{caption.strip()}'\n" if caption and caption.strip() else ""
            community_clause = ""
            if community_comments and isinstance(community_comments, list):
                clean_comms = [c.strip() for c in community_comments if c and c.strip()]
                if clean_comms:
                    community_clause = f"Existing comments: {clean_comms[:3]}\nMake your comment distinct from these.\n"

            prompt = (
                f"Your Persona: '{active_persona}'. "
                f"Look at this screenshot of an Instagram Reel and its caption. Is it predominantly about {topic}? "
                "If NO, reply strictly with the word: NO. "
                "If YES, write a natural, conversational comment in 6 to 18 words about a specific visual detail. "
                f"{author_clause}"
                f"{caption_clause}"
                f"{community_clause}"
                f"{sentiment_guidance} "
                "NO hashtags. Maximum of 1 basic emoji. DO NOT use generic filler like 'beautiful', 'awesome', 'cute'. "
                "NEVER use em-dashes (— or –). NEVER sound like an AI assistant or bot. "
                "Speak naturally and casually with a slight, subtle Aussie flavour (e.g. subtle phrasing like 'reckon', 'heaps', 'ripper', 'mate', 'cheers', 'keen', but keep it subtle and tone-appropriate)."
            )
            
            model = genai.GenerativeModel(
                model_name='gemini-3.6-flash',
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
            
            with _track_vision():
                response = model.generate_content(
                    img,
                    safety_settings=safety_settings,
                    request_options={"timeout": 30.0}
                )
            
            answer = _safe_extract_text(response).strip()
            if not answer or answer.upper() == "NO":
                return ""

            cleaned = _sanitize_response(answer)
            if not cleaned:
                return ""

            # CO-116: Check against CommentMemory to avoid repetition
            if memory is not None and hasattr(memory, "is_similar_to_recent"):
                if memory.is_similar_to_recent(cleaned, threshold=0.55):
                    logger.info(
                        f"Reel comment '{cleaned}' is too similar to recent history. Using novel sentiment fallback."
                    )
                    cleaned = generate_sentiment_fallback(
                        sentiment=sentiment, author=author, memory=memory
                    )

            if memory is not None and hasattr(memory, "add_comment") and cleaned:
                memory.add_comment(
                    cleaned,
                    target_username=author,
                    sentiment=sentiment,
                    post_type="reel",
                )

            return cleaned
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Reel Vision Evaluation Failed: {error_msg}")
            if "429" in error_msg or "Quota exceeded" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if re.search(r"GenerateRequestsPerDay|daily|limit:\s*20\b", error_msg, re.IGNORECASE):
                    logger.warning(
                        "Daily Gemini Vision free-tier quota exhausted. Tripping circuit breaker for session."
                    )
                    VISION_API_DEAD = True
                    break
                wait_time = 60
                m = re.search(r"retry in ([\d\.]+)s", error_msg)
                if not m:
                    m = re.search(r"seconds:\s*(\d+)", error_msg)
                if m:
                    wait_time = int(float(m.group(1))) + 5
                _safe_rate_limit_sleep(wait_time, attempt, 3, context="Reel Comment")
                continue
            elif re.search(r"\b401\b", error_msg) or "UNAUTHENTICATED" in error_msg or "API_KEY_INVALID" in error_msg:
                logger.error("Circuit Breaker Activated (Invalid Auth). Disabling Vision AI for session.")
                VISION_API_DEAD = True
                break
            break
    return ""

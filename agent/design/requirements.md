# Project Requirements: InstaAddict

**Project Name**: InstaAddict  
**Version**: 1.1.0  
**Created**: 2026-09-11  
**Last Updated**: 2026-09-13  
**Status**: Active  

---

## Overview

InstaAddict is an advanced, production-grade Instagram automation bot written in Python that interacts directly with an Android device or emulator running the official Instagram app (tested up to v446+) via `uiautomator2` and native `adb`. It faithfully simulates human behavior (scroll physics, typing cadences, randomized intervals, like/follow ratios, story watching) to grow organic audience engagement safely without touching private, reverse-engineered APIs that trigger account bans.

InstaAddict is an active continuation and evolution of the GramAddict project, fundamentally rebuilt with modern Instagram UI compatibility, AI multimodal reasoning, resilient ad/browser escape watchdogs, dynamic hashtag optimization, and persistent caching.

---

## Goals and Architectural Subsystems

### 1. Modern Instagram (v446+) & Reels Compatibility
- **Full-Screen Reels Interaction**: Support browsing, liking, and commenting on full-screen video Reels opened from hashtag feeds, profile grids, and explore.
- **Multi-Tier Author Resolution**: Locate post authors across both traditional feed locators (`ROW_FEED_PHOTO_PROFILE_NAME`) and modern Clips locators (`CLIPS_AUTHOR_USERNAME`, regex content description matching on `CLIPS_AUTHOR_PROFILE_PIC`, `ROW_FEED_PROFILE_HEADER`, `CLIPS_AUTHOR_INFO_COMPONENT`).
- **Decoupled Ad Detection**: Ensure missing or non-clickable author elements do not falsely trigger advertisement classification or skips on organic content.
- **Native Reels Like Button**: Seamlessly toggle likes on `ResourceID.LIKE_BUTTON` in addition to feed heart icons.
- **Fast Caption Extraction**: Extract captions from `CLIPS_CAPTION_COMPONENT` with zero redundant scroll loops.

### 2. Tiered Masterlist & Dynamic Hashtag Discovery Engine (`HashtagManager`)
- **4-Tier Curated Masterlist**: Organize hashtag discovery pools into Local Community, Breed/Niche, Lifestyle/Adventure, and Reach/Community tiers (`accounts/<username>/hashtags.yml`).
- **Multi-Strategy Expansion**:
  - *Strategy 1 (Gemini AI Expansion)*: Dynamically synthesize trending and high-conversion niche tags tailored to the account's persona.
  - *Strategy 2 (Zero-Overhead Caption Harvester)*: Silently extract and frequency-track `#tag` occurrences from scanned post captions during regular runs.
- **Deterministic Governance Rules**:
  - *Addition Rules (R-ADD-1..4)*: Enforce multi-session observation thresholds, anti-spam blacklists, semantic relevance keywords, and tier classification.
  - *Rotation Rules (R-ROT-1..3)*: Proportional tier-balanced sampling (2:2:1:1), 2-session anti-fatigue cooldowns, and randomized sequence execution.
  - *Pruning Rules (R-PRN-1..2)*: Auto-prune 0-result dead tags and enforce 7-day saturation benching on over-liked tags.

### 3. Persistent Non-Bot Followings Cache
- **O(1) Memory Lookups & Atomic Storage**: Persist known non-bot followings in `accounts/<username>/non_bot_followings.json` using atomic temporary file renames.
- **Fast-Skip Unfollow Engine**: Pre-seed and fast-skip organic accounts during unfollow runs, avoiding repetitive element polling and log noise.
- **Lifecycle Invalidation**: Automatically purge accounts from the cache when followed or unfollowed by the bot.

### 4. Advanced Ad Detection & In-App Browser Escape Watchdog
- **Universal Ad Detection**: Multi-vector evaluation (sponsored labels, server components, post-relative bounded CTA button coordinates) across feeds, hashtags, places, and likers.
- **Watchdog Recovery**: Detect and dismiss `BrowserLiteInMainProcessIGActivity` and external Chrome overlays using native close buttons, fallback back-presses, and foreground app relaunching.
- **Package Whitelisting**: Protect core Android OS interfaces (`systemui`, IME keyboards) from false-positive dismissals.

### 5. Multimodal Vision AI Engagement & Autonomous Uploader
- **Gemini Vision AI (`gemini-2.5-flash`)**: High-accuracy visual post analysis, contextual commenting matching account personas (`ai-persona.yml`), and single-shot evaluate-and-comment to halve API requests.
- **Quota & Safety Resilience**: 429 exponential backoff retries, 512x512 LANCZOS payload compression, and FinishReason safety sanitizers.
- **Content Queue Uploading (`UploadPostsPlugin`)**: Headless image/video upload automation from `accounts/<username>/upload_queue/` with automatic aspect ratio cropping, video trimming, and AI-generated captioning.

### 6. Fluid ADB-Native Motion & Human Simulation
- **Native Flick Gestures**: Discarded jerky `uiautomator2.drag` in favor of calibrated 200ms `adb shell input swipe` gestures.
- **Single-Swipe Reels Scroll**: Single vertical flick (80% down to 20% height) for seamless video feed navigation, eliminating multi-jerk delays.
- **Task Sequence Randomizer**: Randomize job execution orders (`--randomize-tasks`) to avoid predictable bot patterns.

### 7. Production Telemetry & Self-Learning Optimizer
- **Resilient Crash Logging**: Global `sys.excepthook` interceptor capturing third-party crashes in `_error_trace.log` before process exit.
- **Windows File Lock Safety**: Explicit descriptor unlinking for RotatingFileHandlers, eliminating `[WinError 32]` collisions.
- **Continuous Markdown History**: Non-overwritten session logs in `history.md` and timestamped session summaries in `reports/`.
- **Dogfood Self-Learning Optimizer (`dogfood.py`)**: Automated log parsing and conversion analytics yielding dynamic parameter tuning recommendations (`tuning_suggestions.md`).

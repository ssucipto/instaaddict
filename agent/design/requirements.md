# Project Requirements: InstaAddict

**Project Name**: InstaAddict  
**Version**: 1.2.1  
**Created**: 2026-09-11  
**Last Updated**: 2026-09-17  
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
- **Gemini Vision AI (`gemini-3.6-flash`)**: High-accuracy visual post analysis, contextual commenting matching account personas (`ai-persona.yml`), single-shot evaluate-and-comment to halve API requests, and mandatory pre-upload caption elaboration.
- **5-Attempt Exponential Backoff Retries**: Up to 5 retries with backoff delays ($2s, 4s, 6s, 8s$) across Gemini Vision inference and HashtagManager tag retrieval on transient HTTP 500, 503, and 504 Deadline Exceeded conditions.
- **Autonomous Uploader (`UploadPostsPlugin`)**: Headless image/video upload automation from `accounts/<username>/content_queue/pending/` with automatic MediaStore discovery, 12-hour publication rate-limiting, and upload queue prioritization at session start.
- **Two-Way Telegram Bot Ingestion**: Real-time two-way inbox polling (`telegram-inbox: true`, `scripts/check_telegram.py`), companion comment attachment to media sidecars, and interactive `/elaborate` and `/caption` commands.

### 6. Fluid ADB-Native Motion & Human Simulation
- **Native Flick Gestures**: Discarded jerky `uiautomator2.drag` in favor of calibrated 200ms `adb shell input swipe` gestures.
- **Single-Swipe Reels Scroll**: Single vertical flick (80% down to 20% height) for seamless video feed navigation, eliminating multi-jerk delays.
- **Task Sequence Randomizer**: Randomize job execution orders (`--randomize-tasks`) to avoid predictable bot patterns.

### 7. Production Telemetry & Self-Learning Optimizer
- **Resilient Crash Logging**: Global `sys.excepthook` interceptor capturing third-party crashes in `_error_trace.log` before process exit.
- **Windows File Lock Safety**: Explicit descriptor unlinking for RotatingFileHandlers, eliminating `[WinError 32]` collisions.
- **Continuous Markdown History**: Non-overwritten session logs in `history.md` and timestamped session summaries in `reports/`.
- **Dogfood Self-Learning Optimizer (`dogfood.py`)**: Automated log parsing and conversion analytics yielding dynamic parameter tuning recommendations (`tuning_suggestions.md`).

### 8. Modal Dialog Dismissal, Rate Instagram Handling & Security Isolation
- **Universal Modal Dialog Dismissal Engine (`UniversalActions.dismiss_dialog`)**: Safe non-destructive popup dismissal prioritizing negative options ("No, thanks", "Remind me later", "Not now", "Cancel", "Maybe later", "Skip", "Close"), informational fallback ("OK", "Got it", "Continue"), and Android system ANRs ("Wait").
- **Strict "Rate Instagram" Handling**: Strictly bypasses Play Store redirection by matching and clicking "No, thanks" while rejecting "Rate Instagram".
- **Post-Upload Sweeping**: 3-iteration dialog sweep immediately following post publication to ensure subsequent jobs are not obstructed.
- **4-Tier Escalated Stuck-Screen Recovery (`UniversalActions.recover_stuck_screen`)**: Dialog dismissal -> Android back key sequences -> Home tab navigation -> clean application restart (`app_stop` + `app_start`).
- **Subprocess & OS Command Hardening (OWASP A03:2021)**: Elimination of `shell=True` from all core execution paths (`utils.py`, `device_facade.py`), replaced with parameterized lists and explicit defensive timeouts.
- **Privacy Decoupling & Secret Isolation**: Complete eradication of hardcoded personal identifiers, bot tokens, or private credentials from tracked files; generic fallback creator defaults for personas and hashtags.


# InstaAddict-AI: Complete User & Operator Guide

> **InstaAddict-AI (Enhanced Edition)**: Human-like, autonomous Instagram growth and fleet management powered by native ADB, UIAutomator2, multimodal Vision AI, and resilient multi-process orchestration.
> **No Root Required. No Private APIs. Zero Ban Risk when operated within human limits.**

---

## Table of Contents

1. [System Architecture & Core Philosophy](#1-system-architecture--core-philosophy)
2. [Prerequisites & Environment Setup](#2-prerequisites--environment-setup)
   * [Python & System Dependencies](#python--system-dependencies)
   * [Android Device / Emulator Setup](#android-device--emulator-setup)
3. [Single-Account Mode (Classic Operation)](#3-single-account-mode-classic-operation)
   * [Creating an Account Profile](#creating-an-account-profile)
   * [Configuring Actions, Limits & Working Hours](#configuring-actions-limits--working-hours)
   * [Running the Bot](#running-the-bot)
4. [Multi-Account Fleet Orchestration (Milestone 11)](#4-multi-account-fleet-orchestration-milestone-11)
   * [Overview & Multi-Process Architecture](#overview--multi-process-architecture)
   * [Configuring `multi_config.yml`](#configuring-multi_configyml)
   * [Starting the Fleet Supervisor](#starting-the-fleet-supervisor)
   * [Interactive Live TUI Dashboard Views](#interactive-live-tui-dashboard-views)
   * [Keyboard Shortcuts & Zero-Downtime Hot Reload](#keyboard-shortcuts--zero-downtime-hot-reload)
   * [Headless Server Execution](#headless-server-execution)
   * [CLI Management Subcommands](#cli-management-subcommands)
5. [Multimodal Vision AI & Smart Engagement](#5-multimodal-vision-ai--smart-engagement)
   * [Google Gemini API Key Setup](#google-gemini-api-key-setup)
   * [AI Personas & Australian Dog Voice Vernacular](#ai-personas--australian-dog-voice-vernacular)
   * [Quota Optimization & 429 Exponential Backoff](#quota-optimization--429-exponential-backoff)
6. [Autonomous Content Queue & Auto-Uploader](#6-autonomous-content-queue--auto-uploader)
   * [Queue Directory Structure](#queue-directory-structure)
   * [Sidecar Captions & Hashtag Enrichment](#sidecar-captions--hashtag-enrichment)
   * [Rate Limits & Cooldowns](#rate-limits--cooldowns)
7. [Two-Way Telegram Assistant & Mobile Control](#7-two-way-telegram-assistant--mobile-control)
   * [Configuring Telegram Ingestion](#configuring-telegram-ingestion)
   * [Remote Media Queueing from Mobile](#remote-media-queueing-from-mobile)
   * [Interactive Bot Commands](#interactive-bot-commands)
   * [Multi-Account Fleet Targeting via Telegram](#multi-account-fleet-targeting-via-telegram)
8. [Autonomous Reliability & Safety Shields](#8-autonomous-reliability--safety-shields)
   * [3-Tier BotWatchdog Recovery](#3-tier-botwatchdog-recovery)
   * [Universal Ad Avoidance & Browser Escape Watchdog](#universal-ad-avoidance--browser-escape-watchdog)
   * [Zero-Displacement Grid Trap Breakers](#zero-displacement-grid-trap-breakers)
   * [Fast ADB Metadata Fallback](#fast-adb-metadata-fallback)
   * [Targeted ADB Reconnect Isolation](#targeted-adb-reconnect-isolation)
9. [Self-Learning Dogfood Optimizer & Fleet Telemetry](#9-self-learning-dogfood-optimizer--fleet-telemetry)
   * [Historical Session Recording](#historical-session-recording)
   * [Automated Filter Tuning Suggestions](#automated-filter-tuning-suggestions)
   * [Fleet Aggregation & Markdown/JSON Reports](#fleet-aggregation--markdownjson-reports)
10. [Troubleshooting & FAQ](#10-troubleshooting--faq)

---

## 1. System Architecture & Core Philosophy

Traditional Instagram bots rely on reverse-engineered private REST/GraphQL APIs. Instagram instantly flags and bans these bots using TLS fingerprinting, request pattern analysis, and header discrepancies.

**InstaAddict-AI operates differently**:
* It interacts exclusively with the **official Instagram Android application** running on real hardware or Android emulators.
* It uses **UIAutomator2** for layout discovery and native **ADB shell inputs** for fluid human-like gestures (200ms flick swipes, natural typing cadences, random pauses).
* It preserves the device's unique hardware identifiers, IMEI, MAC address, and carrier info.
* In **Multi-Account Mode**, each account runs inside its own **isolated OS subprocess** bound to a dedicated Android emulator instance. Memory leaks, singleton states, and crashes in one account cannot destabilize sibling accounts.

```
                    ┌────────────────────────────────────────────────────────┐
                    │            InstaAddict-AI AccountOrchestrator          │
                    │   (Exclusive PID Lock, Bounded Logs, Hot-Reload Engine) │
                    └───────┬───────────────────┬───────────────────┬────────┘
                            │                   │                   │
               ┌────────────▼──────────┐ ┌──────▼──────────┐ ┌──────▼──────────┐
               │    Bot Subprocess 1   │ │ Bot Subprocess 2│ │ Bot Subprocess N│
               │ (@brand_one / PID A)  │ │(@shop_two/PID B)│ │(@blog_n / PID C)│
               └───────────┬───────────┘ └──────┬──────────┘ └──────┬──────────┘
                           │                    │                   │
                  ┌────────▼───────┐   ┌────────▼───────┐  ┌────────▼───────┐
                  │ Android AVD 1  │   │ Android AVD 2  │  │ Android AVD N  │
                  │(emulator-5554) │   │(emulator-5556) │  │(emulator-5558) │
                  └────────────────┘   └────────────────┘  └────────────────┘
```

---

## 2. Prerequisites & Environment Setup

### Python & System Dependencies
* **Python**: 3.11, 3.12, or 3.13.
* **Operating System**: Windows 10/11, Linux (Ubuntu, Debian, Fedora, Arch), or macOS.
* **Android Platform Tools (ADB)**: Ensure `adb` is installed and on your system `PATH`. Test with:
  ```bash
  adb version
  ```

#### Virtual Environment Installation
```bash
git clone https://github.com/ssucipto/instaaddict.git
cd instaaddict

# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Linux / macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Android Device / Emulator Setup
You can use physical Android devices via USB/Wi-Fi or Android emulators:
* **Recommended Emulators**: Android Studio AVD, BlueStacks 5 (Pie 64-bit or Android 11), LDPlayer 9, or Nox.
* **Resolution**: 1080x1920 (FHD) or 720x1280 (HD) with 320 to 480 DPI.
* **Instagram App**: Install the official Instagram app (tested up to v447+) from the Google Play Store or APKMirror. Log into your account manually on each emulator.
* **Verify ADB Connection**:
  ```bash
  adb devices
  ```
  Output should list your emulator(s), for example:
  ```text
  List of devices attached
  emulator-5554   device
  emulator-5556   device
  ```

---

## 3. Single-Account Mode (Classic Operation)

### Creating an Account Profile
Initialize a new profile configuration in the `accounts/` directory:
```bash
python run.py init my_account
```
This generates the profile directory:
```text
accounts/my_account/
├── config.yml           # Primary bot configuration & job schedule
├── filters.yml          # Filtering criteria (followers range, business account rules)
├── hashtags.yml         # Curated 4-tier hashtag pools
├── whitelist.txt        # Profiles never to unfollow
├── blacklist.txt        # Profiles/keywords never to interact with
├── content_queue/       # Autonomous upload staging directory
└── telegram.yml         # Optional remote Telegram bot config
```

### Configuring Actions, Limits & Working Hours
Edit `accounts/my_account/config.yml`:
```yaml
# Account Credentials & Device
username: my_account
device: emulator-5554
app-id: com.instagram.android

# Working Hours (24-hour format: HH.MM-HH.MM)
working-hours: 09.00-22.30

# Speed & Delays
speed: 2                 # 1 = conservative, 2 = balanced, 3 = fast
total-crashes-limit: 5   # Max allowable crashes before self-terminating

# Interaction Safety Limits (Per Session)
total-likes-limit: 30-50
total-follows-limit: 10-20
total-unfollows-limit: 15-25
total-comments-limit: 5-10
total-watch-stories-limit: 40-60

# Scheduled Interaction Jobs
feed: 10-20
interact-reels: 10-15
hashtag-posts-recent: 15-25
blogger-followers: 10-20
unfollow: 15-20
```

### Running the Bot
Launch the single-account bot:
```bash
python run.py --config accounts/my_account/config.yml
```
To override the emulator serial from the command line:
```bash
python run.py --config accounts/my_account/config.yml --device emulator-5556
```

---

## 4. Multi-Account Fleet Orchestration (Milestone 11)

### Overview & Multi-Process Architecture
Milestone 11 enables supervising multiple independent accounts concurrently across multiple emulators from a single terminal interface.

Key features:
* **Exclusive PID Locking**: Prevents accidental duplicate supervisors from clobbering state (`logs/orchestrator/orchestrator.pid`).
* **Bounded Log Rotation**: Automatically rotates child stdout files (`logs/orchestrator/{username}_stdout.log`) when exceeding 10MB.
* **Emulator Boot Assertion**: Validates `sys.boot_completed == "1"` and `init.svc.bootanim == "stopped"` before starting accounts.
* **Targeted ADB Transport Isolation**: Never terminates the global ADB server during multi-account runs.
* **Zero-Downtime Hot Reload**: Add or disable accounts on the fly without interrupting running bots.

### Configuring `multi_config.yml`
Copy `config-examples/multi_config.yml` to your project root:
```yaml
orchestrator:
  max_concurrent: 4               # Max accounts running simultaneously
  stagger_start_seconds: "10-20"  # Delay between account boots (prevents CPU spikes)
  health_check_interval: 10       # Seconds between health checks
  auto_restart: true              # Automatically recover crashed accounts
  max_restart_attempts: 3         # Consecutive restart limit per account
  log_dir: logs/orchestrator      # Directory for supervisor and stdout logs

# Global filters inherited by all accounts
global_blacklist:
  - accounts/global_blacklist.txt
global_whitelist:
  - accounts/global_whitelist.txt

# Account definitions
accounts:
  - username: brand_alpha
    config: accounts/brand_alpha/config.yml
    device: emulator-5554
    enabled: true
    priority: 1
    gemini_api_key: AIzaSyAlphaKey...   # Optional per-account API key

  - username: store_beta
    config: accounts/store_beta/config.yml
    device: emulator-5556
    enabled: true
    priority: 2

  - username: influencer_gamma
    config: accounts/influencer_gamma/config.yml
    device: emulator-5558
    enabled: false                      # Disabled accounts are skipped
    priority: 3
```

### Starting the Fleet Supervisor
Start the fleet orchestrator with the live Rich TUI dashboard:
```bash
python run.py multi
# Or with explicit configuration path:
python run.py multi --config multi_config.yml
```

### Interactive Live TUI Dashboard Views
The dashboard provides real-time visibility into all running bot processes with under 0.5% CPU overhead.

Press **`[Tab]`** to cycle through 3 distinct display modes:
1. **Mode 1: Fleet Summary Table**:
   * Shows account usernames, assigned emulator serials, process PIDs, running states, and current real-time session KPIs (Likes, Follows, Comments, Stories Watched, Uptime).
2. **Mode 2: Detailed Account Cards**:
   * Displays per-account device battery/power status, working hours window, next scheduled wake-up time, and error trace previews.
3. **Mode 3: Fleet Telemetry Funnel**:
   * Aggregates total actions across all accounts, displays conversion ratios, and visualizes overall fleet health.

### Keyboard Shortcuts & Zero-Downtime Hot Reload
While the live TUI dashboard is active:
* **`[Tab]`**: Switch between Table, Cards, and Telemetry views.
* **`[C]`**: **Hot-Reload Configuration**. Edit `multi_config.yml` in another editor, press `[C]`, and the orchestrator immediately:
  * Spawns newly added or newly enabled accounts.
  * Gracefully stops removed or disabled accounts.
  * Leaves already-running accounts 100% uninterrupted.
* **`[Q]`** or **`Ctrl+C`**: Initiates dual-phase graceful termination for all managed accounts.

### Headless Server Execution
To run in cloud environments, Docker containers, or background sessions without ANSI escape codes:
```bash
python run.py multi --no-tui
```

### CLI Management Subcommands
Manage or query a running fleet from a second terminal:

* **Query Fleet Status**:
  ```bash
  python run.py multi --status
  ```
* **Run Only One Specific Account Under the Orchestrator**:
  ```bash
  python run.py multi --only brand_alpha
  ```
* **Trigger Remote Hot-Reload**:
  ```bash
  python run.py multi --reload
  ```
* **Stop a Specific Account Gracefully**:
  ```bash
  python run.py multi --stop @brand_alpha
  ```
* **Stop All Accounts and Terminate the Fleet**:
  ```bash
  python run.py multi --stop
  ```

---

## 5. Multimodal Vision AI & Smart Engagement

InstaAddict-AI integrates the **Google Gemini 3.6 Flash** model to analyze photos and Reels visually, writing human-like, contextual comments matching your account's exact persona.

### Google Gemini API Key Setup
Set your Gemini API key in your system environment:
```bash
# Windows (PowerShell)
$env:GEMINI_API_KEY="AIzaSyYourKeyHere..."

# Linux / macOS
export GEMINI_API_KEY="AIzaSyYourKeyHere..."
```
Alternatively, in `multi_config.yml`, define a separate `gemini_api_key` for each account to distribute API quotas across multiple keys.

### AI Personas & Australian Dog Voice Vernacular
Configure the AI voice in `accounts/<username>/ai-persona.yml`:
```yaml
persona:
  name: "Barnaby"
  species: "Kelpie / Australian Working Dog"
  tone: "Friendly, enthusiastic, authentic Aussie working dog"
  vocabulary_hints:
    - "reckon"
    - "heaps"
    - "ripper"
    - "mate"
    - "cheers"
    - "keen"
  rules:
    - "Keep comments short: 3 to 6 words maximum."
    - "Always sound genuine and comment on specific visual elements in the post."
    - "Never use corporate marketing jargon."
```
* **Anti-AI Formatting Sanitizer**: Automatically cleans AI-generated comments, removing synthetic em-dashes (`—`) and en-dashes (`–`) to keep formatting 100% natural.

### Quota Optimization & 429 Exponential Backoff
* **Single-Shot Evaluation**: Combines post relevance filtering and comment generation into a single API request, cutting API calls by 50%.
* **LANCZOS Compression**: Downsamples screenshots to 512x512 before uploading to Gemini, reducing payload size by ~80%.
* **Exponential Backoff**: If Google returns HTTP 429 (Resource Exhausted), the bot pauses and retries with randomized backoff delays (2s, 4s, 8s, 16s) rather than crashing.

---

## 6. Autonomous Content Queue & Auto-Uploader

The bot can autonomously publish photos, carousels, and videos to Instagram with automated caption elaboration, aspect ratio adjustment, and hashtag injection.

### Queue Directory Structure
Place media into the pending queue directory:
```text
accounts/<username>/content_queue/
├── pending/
│   ├── puppy_run.jpg
│   ├── puppy_run.txt            # Optional sidecar caption
│   ├── beach_day.mp4
│   └── beach_day.json           # Optional JSON metadata
├── published/                   # Automatically moved here after upload
│   └── 2026-09-25_puppy_run.jpg
└── failed/                      # Moved here if publication fails
```

### Sidecar Captions & Hashtag Enrichment
* **Text Sidecars (`.txt`)**: Simply create a `.txt` file with the same filename as your media. If empty or absent, Vision AI inspects the media and generates a caption automatically.
* **JSON Sidecars (`.json`)**: Specify advanced metadata:
  ```json
  {
    "caption": "Morning sprint across the paddock!",
    "hashtags": ["#kelpie", "#workingdog", "#dogsofinstagram"],
    "first_comment": "Follow for daily adventures!"
  }
  ```
* **Post-Upload Dialog Sweeping**: After publishing, the bot executes an automated 3-pass dialog sweep to dismiss "Share to Facebook" or "Turn on Notifications" prompts, leaving the UI clean for subsequent interaction jobs.

### Rate Limits & Cooldowns
In `accounts/<username>/config.yml`:
```yaml
upload-posts: true
upload-posts-rate-limit-hours: 12   # Enforces minimum 12 hours between uploads
upload-force-square: false          # Set to true to force 1:1 cropping
```

---

## 7. Two-Way Telegram Assistant & Mobile Control

Control your bot and queue posts remotely directly from your smartphone via Telegram.

### Configuring Telegram Ingestion
Create `accounts/<username>/telegram.yml`:
```yaml
telegram-api-token: "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"
telegram-chat-id: "987654321"      # Strict whitelist: ignores unauthorized chat IDs
telegram-inbox: true               # Enables responsive polling
```

### Remote Media Queueing from Mobile
1. Open your Telegram chat with your bot.
2. Send a photo or video.
3. Add your desired caption directly in the photo message.
4. The bot downloads the media, creates the `.txt` sidecar, saves it to `content_queue/pending/`, and replies with a queue confirmation!

### Interactive Bot Commands
Send these commands in your Telegram chat anytime:
* `/status` — Displays current Android device state, running status, session KPIs, working hours, and queue size.
* `/queue` — Previews all pending media waiting in line with thumbnail titles and caption snippets.
* `/preview` — Sends you a photo preview of the next scheduled post.
* `/post` — Triggers an immediate upload of the next pending media (respects cooldown).
* `/post_force` or `/post now` — Bypasses the cooldown timer and publishes immediately.
* `/cooldown` — Checks how much time remains before the next scheduled upload slot.
* `/start instagram` — Wakes up the emulator and starts the Instagram app on demand.

### Multi-Account Fleet Targeting via Telegram
When running multiple accounts:
* **Targeted Status**: `/status @brand_alpha` or `/status @store_beta`
* **Targeted Stop**: `/stop @brand_alpha`
* **Targeted Upload**: When sending a photo to Telegram, prefix the caption with `@brand_alpha`:
  > `@brand_alpha Our weekend sale starts now! #sale`
  The supervisor automatically routes the media exclusively to `accounts/brand_alpha/content_queue/pending/`.

---

## 8. Autonomous Reliability & Safety Shields

InstaAddict-AI is engineered for unattended 24/7 reliability:

1. **3-Tier BotWatchdog Recovery**:
   * **Tier 1 (Soft Recovery)**: Closes dialogs, dismisses keyboard, and navigates back to feed.
   * **Tier 2 (Job Skip)**: Safely advances to the next task if an element repeatedly fails to open.
   * **Tier 3 (Hard App Restart)**: Force-closes Instagram (`am force-stop`) and relaunches cleanly without killing the Python process.
2. **Universal Ad Avoidance & Browser Escape**:
   * Evaluates sponsored labels, CTA buttons, and server ad indicators across all interaction sources.
   * If Instagram opens an in-app browser (`BrowserLiteInMainProcessIGActivity`), the escape watchdog immediately taps the close button or issues back-presses to restore the Instagram app.
3. **Zero-Displacement Grid Trap Breakers**:
   * Resolves thumbnail oscillations on hashtag/location grids by asserting `OpenedPostView.is_post_opened()` before scrolling.
   * Caps unidentifiable author scans at 5 consecutive posts, breaking out of dead hashtag pools automatically.
4. **Fast ADB Metadata Fallback**:
   * If UiAutomator2's RPC gateway hangs or disconnects (common during Android 17 emulator ANRs), device metadata (`getprop`, `wm size`, `dumpsys power`) falls back to direct ADB calls in <50ms, eliminating 45-minute hangs.
5. **Targeted ADB Reconnect Isolation**:
   * When an emulator transport drops, the bot executes `adb -s <id> reconnect` targeting only that device, preventing `adb kill-server` from disrupting sibling bots.

---

## 9. Self-Learning Dogfood Optimizer & Fleet Telemetry

### Historical Session Recording
Every session writes structured telemetry to:
* `accounts/<username>/sessions.json`: Machine-readable array of session timestamps, actions taken, crash counts, and durations.
* `accounts/<username>/history.md`: Human-readable markdown audit trail of all sessions.
* `accounts/<username>/reports/`: Timestamped session summary reports.

### Automated Filter Tuning Suggestions
InstaAddict-AI includes an autonomous optimization engine:
```bash
python data_analytics.py --username my_account
```
The **DogfoodOptimizer** analyzes skip reason distributions, failure points, and interaction speeds:
* If 90% of profiles are skipped due to follower count rules, it calculates mathematically balanced thresholds and writes recommendations to `accounts/<username>/tuning_suggestions.md`.
* It differentiates between fatal crashes and normal daily limit completions.

### Fleet Aggregation & Markdown/JSON Reports
In multi-account mode, cross-account metrics are synthesized automatically:
* Generates `logs/orchestrator/fleet_report.md` comparing likes, follows, comments, and crash rates across all accounts.
* Exposes automated process reboot hooks for continuous self-tuning pipelines.

---

## 10. Troubleshooting & FAQ

#### Q: ADB says "device offline" or emulator not detected.
* **Fix**: Run `adb kill-server && adb start-server`. Verify that USB Debugging is enabled in your emulator's Developer Options. If using BlueStacks or LDPlayer, ensure "ADB Connection" is toggled ON in the emulator settings.

#### Q: UiAutomator2 times out or throws GatewayError.
* **Fix**: InstaAddict-AI includes automated direct ADB fallbacks. However, if an emulator's Android system server freezes, restart the emulator. Ensure the emulator has at least 2 CPU cores and 4GB RAM allocated.

#### Q: The bot sleeps and says "Outside working hours".
* **Fix**: Check `working-hours` in `config.yml`. It uses 24-hour format: `HH.MM-HH.MM` (e.g. `09.00-23.00` or `00.00-23.59` for 24/7 operation).

#### Q: How do I run multiple accounts on the same computer?
* **Fix**: Open multiple emulator instances (each will receive a unique port like `emulator-5554`, `emulator-5556`). Log into Account A on Emulator 1, and Account B on Emulator 2. Configure `multi_config.yml` and run `python run.py multi`.

#### Q: How do I stop the bot safely without corrupting data?
* **Fix**: Press **`[Q]`** in the multi-account TUI, press **`Ctrl+C`** in single-account mode, or send `/stop` in Telegram. The bot detects the stop sentinel, finalizes the active interaction, writes atomic session files, and exits cleanly.

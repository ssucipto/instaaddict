# Design Document: Terminal User Interface (TUI) & Live Dashboard

**Title**: Terminal User Interface (TUI) & Live Dashboard  
**Status**: Planned  
**Created**: 2026-09-17  
**Last Updated**: 2026-09-17  
**Author**: Antigravity  

---

## 1. Overview & Problem Statement

### 1.1 Context
InstaAddict is a high-throughput, multi-threaded mobile automation engine that executes complex workflows:
- Reels watching and engagement
- Multi-tier hashtag rotation and discovery
- Multimodal Gemini Vision AI evaluation and contextual commenting
- Media queue management and headless Instagram publishing
- 4-tier navigation recovery and ad avoidance

### 1.2 Problem
Currently, InstaAddict streams all runtime information linearly to `stdout` via `colorama`. While functional, this approach presents critical usability challenges during long bot sessions:
1. **Console Scroll-Off**: Key metrics (likes count, follows count, session limits, crash counts) scroll off the terminal window within seconds as logs flow.
2. **Lack of Visual Progress**: Users cannot observe at a glance how close the session is to configured safety limits or when the next action will occur.
3. **Log Clutter**: Informational messages, countdown carriage returns (`\r`), and debug traces interleave and visually collide, making it difficult to discern current bot activity from historical background events.
4. **No Real-Time Activity Focus**: Users cannot immediately see which job is currently active, which account is being evaluated, or the remaining duration of cooldown sleeps without searching through scrolling text.

### 1.3 Solution
Design and implement a modern, high-performance, live-updating Terminal User Interface (TUI) using `rich`. The dashboard provides:
- **Persistent Header Banner**: Active account, followers/following, device serial, connection state, session elapsed time.
- **Real-Time Stats & Limits Grid**: Visual progress bars representing progress toward configured safety limits (likes, follows, unfollows, comments, watches, uploads, crashes).
- **Active Context Panel**: Current job, current target post/user, current step (e.g. "Vision AI evaluating Reel..."), and live sleep countdown.
- **Dedicated Rolling Log Window**: Real-time streaming log panel with color-coded level tags and timestamps, isolated from metric panels to eliminate screen flicker or layout corruption.
- **Graceful Headless Fallback**: Automatic detection of non-interactive terminals (`not sys.stdout.isatty()`) or `--no-tui` flags with fallback to standard stream output.

---

## 2. Layout & Visual Specification

```text
+------------------------------------------------------------------------------------------------------------------+
|  [BOT] InstaAddict AI v1.2.1 | @account_name (1,452 followers) | Device: emulator-5554 (Online) | Session #1     |
+------------------------------------------------------+-----------------------------------------------------------+
| SESSION STATS & PROGRESS                             | LIVE LOGS & CONSOLE STREAM                                |
|                                                      | [21:45:02] [INFO] Loaded hashtags pool (64 tags)          |
| Metric          Progress           Count / Limit     | [21:45:10] [INFO] Swiping Reels feed (200ms flick)...     |
| Likes           [========....] 35%   105 / 300       | [21:45:12] [INFO] Found post by @street_pup (organic)     |
| Follows         [======......] 24%    12 /  50       | [21:45:14] [INFO] Gemini Vision AI: Evaluated Reel (0.42s)|
| Unfollows       [............]  0%     0 /  50       | [21:45:15] [INFO] Commented: "Love the energy here!"     |
| Comments        [==========..] 40%     4 /  10       | [21:45:18] [INFO] Liked Reel successfully (selected: True)|
| Watched         [========....] 32%    16 /  50       | [21:45:22] [DEBUG] Cooldown delay: 14s...                 |
| Uploads         [============]100%     1 /   1       |                                                           |
| Crashes         [............]  0%     0 /   5       |                                                           |
| Total Actions   [======......] 28%   138 / 500       |                                                           |
+------------------------------------------------------+                                                           |
| CURRENT ACTIVITY & CONTEXT                           |                                                           |
| * Active Job: interact-hashtag-posts (#doglovers)    |                                                           |
| * Target Post: @street_pup (Post ID: 3418291029)     |                                                           |
| * Subsystem: Gemini Vision AI Commenting             |                                                           |
| * Status: Cooldown sleep (08s remaining)...          |                                                           |
| * Next Upload: 11h 22m cooldown active               |                                                           |
+------------------------------------------------------+-----------------------------------------------------------+
| [Q/Ctrl+C] Graceful Stop  |  [D] Toggle Debug Logs  |  [H] Help  |  Status: RUNNING  |  Working Hours: Active        |
+------------------------------------------------------------------------------------------------------------------+
```

---

## 3. Architecture & Components

### 3.1 Data Model: `DashboardState`
Stores:
- Account & Device metadata
- Session index, duration, start time
- Action metrics vs limits (likes, follows, unfollows, comments, watches, uploads, crashes, total interactions)
- Activity context (job, target, sub-operation, countdown)
- Rolling log deque with max capacity

### 3.2 Logging Bridge: `TuiLogHandler`
- Extends `logging.Handler`.
- Formats incoming records into `rich.text.Text`.
- Appends to `DashboardState.logs_buffer`.
- Thread-safe with locking.

### 3.3 Lifecycle Manager: `DashboardManager`
- Uses `rich.live.Live(auto_refresh=True, refresh_per_second=4)`.
- Rebuilds and renders layout dynamically.
- Gracefully restores terminal state on exit.

---

## 4. Error Handling & Fallback Guarantees
1. **TTY Detection**: Automatically disabled when non-interactive or redirected.
2. **CLI Override**: `--no-tui` explicitly disables the dashboard.
3. **Signal Safety**: Safe cleanup on `KeyboardInterrupt` and `SystemExit`.

---
id: route-045
title: Two-Way Telegram Content Ingestion, Remote Photo Queueing, and Interactive Bot Commands
task_type: feature-integration
milestone: milestone-9-telegram-two-way-ingestion
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-047-telegram-system-capabilities-and-architecture.md
  - agent/memory/decisions.md
files_affected:
  - InstaAddict/plugins/telegram.py
  - InstaAddict/plugins/upload_posts.py
  - InstaAddict/core/utils.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/device_facade.py
  - test/test_telegram_inbox.py
tokens_est: 9500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-14
completed: 2026-09-14
override_reason:
---

## Description
Implement a complete two-way mobile Telegram workflow allowing the user to send full-resolution photos and captions directly from their mobile phone to the InstaAddict bot, automatically staging them into `accounts/<username>/content_queue/pending/` for publication by `UploadPostsPlugin`.

Key Components:
1. **Inbox Polling & Update ID Offset Tracking**:
   - Query Telegram Bot API `getUpdates` with `offset=last_update_id + 1`.
   - Persist processed offset state atomically in `accounts/<username>/telegram_state.json`.
2. **Strict Whitelist Authorization**:
   - Check `message.chat.id` against `telegram-chat-id` configured in `accounts/<username>/telegram.yml` or `config.yml`.
   - Reject unauthorized senders with a security warning.
3. **Photo Ingestion & Sidecar Generation**:
   - Download the highest resolution photo version via `getFile` and Telegram download API.
   - Save the image to `accounts/<username>/content_queue/pending/<id>.jpg`.
   - If a caption is provided with the photo, save it to `<id>.txt` sidecar so `UploadPostsPlugin` uses it as the human text caption.
   - If no caption is sent, leave the image for Gemini Vision AI captioning.
   - Send instant receipt to Telegram: `✅ Photo queued for upload!`.
4. **Interactive Bot Commands**:
   - `/queue`: Lists pending, scheduled, and recently published posts.
   - `/status`: Returns live session statistics (interactions, likes, uploads, crashes, battery/device).
   - `/help`: Displays available commands and quick-start guide.
5. **Responsive Polling During Idle Intervals**:
   - Sliced `wait_for_next_session()` sleep into 20s intervals to poll Telegram inbox so messages and photos are ingested immediately even when the bot is resting between interaction cycles.
6. **Publication Status Notifications**:
   - `UploadPostsPlugin` dispatches a rich Markdown message on publication success (`🚀 Instagram Post Published!`) or failure (`⚠️ Instagram Upload Failed!`).

## Acceptance Criteria
- [x] Unauthenticated Telegram chat IDs cannot queue media or run commands.
- [x] Received photos are saved with `.jpg` extension in `pending/`.
- [x] Accompanying captions are saved to `<basename>.txt` and correctly read by `UploadPostsPlugin`.
- [x] `/queue`, `/status`, and `/help` respond accurately to the authorized user.
- [x] Polling runs during sleep cycles with zero CPU spin.
- [x] 100% test coverage with automated unit tests (`test/test_telegram_inbox.py`).

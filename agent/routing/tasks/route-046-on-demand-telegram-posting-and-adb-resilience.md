---
id: route-046
title: On-Demand Telegram Posting, Subparser CLI Dispatching, and ADB Auto-Recovery
task_type: feature-integration
milestone: milestone-9-telegram-two-way-ingestion
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-052-on-demand-telegram-posting-and-adb-resilience.md
  - agent/memory/patterns.md
files_affected:
  - InstaAddict/__main__.py
  - InstaAddict/plugins/upload_posts.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/device_facade.py
  - InstaAddict/plugins/telegram.py
  - scripts/check_telegram.py
  - test/test_telegram_commands.py
tokens_est: 9500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-15
completed: 2026-09-15
override_reason:
---

## Task Description
Implement on-demand Instagram uploads triggered directly via Telegram bot commands (`/post`, `/post_force`, `/preview`, `/queue`, `/status`), enhance the CLI entrypoint in `__main__.py` to gracefully auto-route flags to `run`, add `--only-upload` mode to execute single uploads in ~45 seconds without running long interaction sessions, and add automatic ADB daemon reconnect logic when the emulator reports offline.

## Acceptance Criteria
- [x] `python -m InstaAddict --username <user>` or `python -m InstaAddict --config <path>` auto-routes to `run` without throwing subparser invalid choice errors.
- [x] `--only-upload` / `--upload-now` restricts `jobs_list` to `["upload-posts"]` and runs exactly 1 session.
- [x] Telegram commands implemented in `telegram.py`:
  - `/post`: Starts upload worker for pending media.
  - `/post_force`: Bypasses 12h cooldown (`--upload-rate-limit-hours 0`) and posts immediately.
  - `/preview`: Sends next queued photo with caption & hashtags to Telegram chat.
  - `/queue` or `/pending`: Lists pending files with statuses.
  - `/status`: Reports device connectivity, app state, and last post timestamp.
- [x] ADB auto-recovery: restarts ADB server if device state is offline or disconnected.
- [x] Full test suite green (127/127 passing) and local CI fast gates pass.
- [x] Unit tests added covering all new commands and options.
- [x] 100% pass across all unit tests.

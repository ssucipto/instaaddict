---
id: route-062
title: Multi-Session Autonomous Looping, Watchdog Heartbeat Instrumentation, and Blogger Follower Hardening
task_type: feature-integration
milestone: null
complexity: medium
executor: Antigravity
context_required:
  - agent/reports/audit-099-multi-session-resilience-and-watchdog-heartbeats.md
  - InstaAddict/core/gemini_vision.py
  - InstaAddict/plugins/action_unfollow_followers.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/core/watchdog.py
  - InstaAddict/core/utils.py
  - accounts/lolatheozjack/config.yml
files_affected:
  - InstaAddict/core/gemini_vision.py
  - InstaAddict/plugins/action_unfollow_followers.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/core/utils.py
  - accounts/lolatheozjack/config.yml
  - test/test_multi_session_resilience.py
tokens_est: 6000
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: '2026-09-20'
completed: '2026-09-20'
override_reason:
---

# Route-062: Multi-Session Autonomous Looping, Watchdog Heartbeat Instrumentation, and Blogger Follower Hardening

## Context & Objectives
Audit #099 identified that `@lolatheozjack` stopped after 44 minutes because it hit `total-crashes-limit: 5`.
Crucially, crashes #4 and #5 were false-positive watchdog back-presses caused by missing heartbeats during 60s Gemini Vision rate limit sleeps and long non-bot fast-skip unfollow loops. Crashes #1-#3 were caused by unhandled `EmptyList` and obsolete `android:id/list` scroll methods in `interact_blogger_followers`. Finally, `stop_bot()` omitted setting `finishTime`, reporting `Completed sessions: 0`.

## Architectural Deliverables

### 1. Watchdog Awareness in Rate Limit Backoff (`InstaAddict/core/gemini_vision.py`)
- In `gemini_vision.py` line 193-206:
  - When sleeping on 429 quota rate limits, chunk the sleep into 5-second intervals.
  - On each chunk, call `record_heartbeat("gemini_vision", f"Rate limit backoff sleep ({elapsed}/{wait_time}s)")`.
  - Wrap the wait in `watchdog.pause()` / `watchdog.resume()` to guarantee the watchdog never sends `KEYCODE_BACK` during legitimate backoffs.

### 2. Watchdog Heartbeat & Safe Row Item Extraction in Unfollow (`InstaAddict/plugins/action_unfollow_followers.py`)
- Call `record_heartbeat("unfollow-followers", f"Iterating followings (checked: {len(checked)})")` on every page iteration in `iterate_over_followings`.
- Wrap `user_name_view.get_text()` in defensive try/except: if `UiObjectNotFoundError` or `JsonRpcError` is raised due to screen animation/recycling, log a debug message and continue to the next item instead of crashing the job.

### 3. Graceful Blogger Follower List Handling (`InstaAddict/core/handle_sources.py`)
- In `handle_sources.py:1088`:
  - When `inspect_current_view` raises `EmptyList`, check `check_and_report_restricted_list()`.
  - If not restricted, log an informative warning (`"Follower list for @{target} is empty or not rendered. Skipping blogger."`), safely navigate back via `device.back()`, and return without re-raising `EmptyList`.
- In `handle_sources.py:1284`:
  - Replace fragile `list_view.scroll(Direction.DOWN)` with fluid gesture swipe (`device.swipe(Direction.BOTTOM)` or `device.swipe_points`) that does not depend on legacy `android:id/list`.
- Add `record_heartbeat("blogger-followers", f"Iterating followers for @{target}")` during followers iteration.

### 4. Session State Finish Time Stamping in `stop_bot()` (`InstaAddict/core/utils.py`)
- In `utils.stop_bot()`:
  - If `session_state` is provided and `session_state.finishTime is None`, set `session_state.finishTime = datetime.now()` before calling `print_full_report()`.
  - Ensures all sessions record valid start and end timestamps.

### 5. Configuration Hardening (`accounts/lolatheozjack/config.yml`)
- Increase `total-crashes-limit: '15'` to prevent transient network/UI recovery events from halting 24/7 autonomous bot operation.

### 6. Automated Unit Testing (`test/test_multi_session_resilience.py`)
- Create unit tests covering:
  - Gemini Vision rate limit sleep watchdog heartbeat and pause behavior.
  - Unfollow followings loop watchdog heartbeat emission and safe `get_text()` error recovery.
  - Blogger followers `EmptyList` graceful skip without crash escalation.
  - Modern gesture swipe fallback for blogger follower lists.
  - `stop_bot()` stamping `finishTime` on `session_state`.

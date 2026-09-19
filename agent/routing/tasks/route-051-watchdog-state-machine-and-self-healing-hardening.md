---
id: route-051
title: Watchdog Escalation State Machine & Self-Healing Resilience Hardening
task_type: feature-integration
milestone: M7
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-075-self-healing-recovery-and-watchdog-resilience.md
  - agent/memory/audit-carryovers.md
  - InstaAddict/core/watchdog.py
  - InstaAddict/core/utils.py
  - InstaAddict/core/tui.py
  - InstaAddict/core/decorators.py
files_affected:
  - InstaAddict/core/watchdog.py
  - InstaAddict/core/utils.py
  - InstaAddict/core/tui.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/plugins/upload_posts.py
  - InstaAddict/core/decorators.py
  - test/test_watchdog.py
  - test/test_runtime_hardening.py
tokens_est: 12000
tokens_actual:
cost_est_usd: 0.00
cost_actual_usd:
created: 2026-09-18
completed: 2026-09-19
override_reason:
---

## Task Description

Address all findings from Audit-075 and resolve carryovers CO-056 and CO-057 to make the bot's self-healing, self-recovery, and watchdog capabilities 100% production-grade and bulletproof:
1. Fix BotWatchdog escalation timer reset bug so Tier 2 (task skip) and Tier 3 (nuclear app relaunch) are reachable during persistent hangs (CO-056).
2. Instrument granular heartbeat emission across countdown(), DashboardState.update_activity(), interact_reels, handle_sources, and upload_posts to prevent false-positive watchdog stall triggers during long healthy operations exceeding 90 seconds (CO-057).
3. Connect UiAutomator2 resurrection logic (`DeviceFacade.ensure_uiautomator_alive()`) into runtime crash handling (`restart()` in `decorators.py`) to recover dropped or crashed accessibility services mid-session.
4. Add safe crash recovery wrappers to modern plugins (`interact-reels` and `upload-posts`).
5. Expand unit test suites to verify multi-tier escalation, granular heartbeats, and zero regressions across existing tests.

## Acceptance Criteria

- [ ] `BotWatchdog` tracks `current_tier` escalation without clobbering `last_heartbeat` in recovery methods.
- [ ] Tier 1 (soft), Tier 2 (skip), and Tier 3 (hard restart) fire in succession when a hang persists past `soft_timeout`, `skip_timeout`, and `hard_timeout`.
- [ ] Genuine heartbeats from main thread reset `current_tier = 0` and `recovering = False`.
- [ ] `countdown()` emits regular heartbeats so long countdown sleeps never trigger the watchdog.
- [ ] `DashboardState.update_activity()` automatically feeds `BotWatchdog.heartbeat()` on active job/action updates.
- [ ] Granular heartbeats emitted in `interact_reels`, `handle_sources`, and `upload_posts` loops for both TUI and headless modes.
- [ ] `restart()` in `decorators.py` calls `device.ensure_uiautomator_alive()` to heal dead instrumentation services before reopening Instagram.
- [ ] `interact-reels` and `upload-posts` run with `@run_safely` exception protection.
- [ ] New unit tests verify escalation sequencing and heartbeat integration in `test/test_watchdog.py`.
- [ ] All 200+ unit tests pass 100% green with zero flake8 lint violations.

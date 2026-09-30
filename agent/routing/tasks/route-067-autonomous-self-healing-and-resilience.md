---
id: route-067
title: Autonomous Self-Healing, Self-Restart, Closed-Loop Tuning & UI Resilience Engine
task_type: feature
milestone: M11
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-135-autonomous-self-healing-and-reliability-architecture.md
  - agent/reports/audit-136-pre-impl-autonomous-self-healing-resilience.md
  - agent/memory/audit-carryovers.md
files_affected:
  - InstaAddict/core/utils.py
  - InstaAddict/core/decorators.py
  - InstaAddict/core/device_facade.py
  - InstaAddict/core/gemini_vision.py
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/navigation.py
  - InstaAddict/core/views.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/__main__.py
  - InstaAddict/core/dogfood.py
  - test/test_autonomous_self_healing_resilience.py
tokens_est: 4500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-10-01
completed: 2026-10-01
override_reason:
---

# Route-067: Autonomous Self-Healing, Self-Restart, Closed-Loop Tuning & UI Resilience Engine

## Objectives

1. **Autonomous Overlay Evasion & Process Life-Cycle (CO-105, CO-110)**:
   - Eliminate fatal `sys.exit(2)` in `decorators.py:restart()`. Replace with an escalating recovery sequence: force-stopping background interference, pausing watchdog, sleeping with backoff, and returning to the session repeat loop without killing Python.
   - Harden `open_instagram()` in `utils.py` to detect and proactively force-stop interfering foreground packages (`com.android.vending`, `com.google.android.gms`, popups, browsers) and dismiss modal overlays before declaring failure.
   - Implement single-account supervisor auto-restart loop in `__main__.py` with exponential backoff on fatal crashes.
   - Auto-proceed on untested IG version prompts in autonomous/daemon runs.

2. **Self-Healing Device & UI Layer (CO-106, CO-107, CO-108, CO-109)**:
   - Build unified `DeviceFacade.take_screenshot()` with validation of image byte headers and instant fallback to `adb exec-out screencap -p` when uiautomator2's `/screenshot/0` returns the 25-byte corrupt error `b'screencap: exit status 1\n'`.
   - Wire `take_screenshot()` into `gemini_vision.py` and `interact_reels.py`, eliminating 100% of `cannot identify image file` PIL exceptions.
   - Replace lingering clicks in `nav_to_hashtag_or_place()` with fast ADB input tap (`< 20ms`) to evade Android long-press thresholds triggering Peek Preview, and support direct in-peek interaction recovery.
   - Modernize `navigateToFollowers()` in `views.py` with adaptive contentDescription and regex text locators for Instagram v447+ profiles.
   - Optimize comment box input focus in `device_facade.py:set_text` to eliminate placeholder mismatch warning spam.

3. **Closed-Loop Self-Tuning (CO-111)**:
   - Hook `DogfoodOptimizer.apply_tuning()` into the post-session completion sequence in `bot_flow.py`.
   - When target pool starvation occurs (`COOLDOWN > 30%`), automatically relax `can-reinteract-after` from 48h to 24h.
   - When Gemini Vision 429 quota exhaustion occurs, automatically throttle `evaluate-percentage` and tune delay means.

4. **Automated Verification**:
   - Create dedicated unit test suite `test/test_autonomous_self_healing_resilience.py` testing all 5 pillars with 100% green pass rate and zero regressions.

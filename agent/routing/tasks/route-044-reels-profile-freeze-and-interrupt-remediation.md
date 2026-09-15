---
id: route-044
title: Reels Profile Story Trapping, 1-2 Minute Freeze Removal, and Exception Interrupt Hardening
task_type: bug-fix-complex
milestone: milestone-8-auto-upload-pipeline
complexity: medium
executor: Antigravity
context_required:
  - agent/reports/audit-045-runtime-errors-and-locator-investigation.md
  - agent/memory/audit-carryovers.md
files_affected:
  - InstaAddict/core/views.py
  - InstaAddict/core/filter.py
  - InstaAddict/core/decorators.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/log.py
tokens_est: 8500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-14
completed: 2026-09-14
override_reason:
---

## Description
Systematically remediate all 5 root causes behind the runtime interaction crash, profile loading freeze, Story trapping, and double-interrupt exception chain:
1. **Always Click Username in Reels (`views.py`)**:
   - For `Owner.OPEN`, exclude `CLIPS_AUTHOR_PROFILE_PIC` from click targets because clicking the avatar in Reels opens the user's Story rather than their profile.
   - Clean usernames (`username.lstrip("@").strip()`) to match `CLIPS_AUTHOR_USERNAME`.
   - In Reels full-screen viewer, prioritize `CLIPS_AUTHOR_USERNAME` to ensure Instagram always navigates to the Profile.
2. **Remove the 1–2 Minute Freeze (`filter.py`)**:
   - Eliminate the 60–120s `random_sleep(60, 120)` when `profile_picture` is missing after 16s.
   - Log a warning and immediately return an unloaded Profile object so `check_profile` skips the profile in 0 seconds.
3. **Catch `EOFError` Across All Interactive Handlers (`decorators.py`, `bot_flow.py`)**:
   - Guard `input("")` in `decorators.py` with `except (KeyboardInterrupt, EOFError):` and cleanly invoke `stop_bot()`.
   - Guard `input()` in `bot_flow.py` for untested IG versions to prevent EOF crashes in headless or detached processes.
4. **Bypass Redundant Media Swipes on Reels (`views.py`)**:
   - Detect when on full-screen Reels viewer (`CLIPS_VIEWER_CONTAINER`, `CLIPS_AUTHOR_USERNAME`).
   - Skip feed media-container search loops (`_find_likers_container` and 4x downward micro-swipes).
   - Directly click `ResourceID.LIKE_BUTTON` and verify without downward swipes.
5. **Protect `sys.excepthook` from Interrupts (`log.py`)**:
   - Wrap disk log emissions in `handle_uncaught_exception` with interrupt-safe suppression (`except (KeyboardInterrupt, SystemExit): sys.exit(0)`) to ensure a double Ctrl-C exits cleanly without raising `Error in sys.excepthook`.

## Acceptance Criteria
- [ ] Reels author interaction clicks `CLIPS_AUTHOR_USERNAME` and never clicks `CLIPS_AUTHOR_PROFILE_PIC` in `Owner.OPEN` mode.
- [ ] Failed profile load exits immediately after 16s with zero seconds of penalty sleep.
- [ ] Headless/detached input prompts never crash with unhandled `EOFError`.
- [ ] Liking on full-screen Reels bypasses feed-container downward swipes.
- [ ] Hitting Ctrl-C during excepthook exits cleanly with code 0.
- [ ] 100% pass rate maintained across all unit tests and new regression tests.

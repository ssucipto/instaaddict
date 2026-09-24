---
id: route-064
title: Hashtag Navigation Verification, Consecutive Unidentifiable Circuit Breaker, and Self-Healing Escape Hardening
task_type: bugfix
milestone: M7
complexity: medium
executor: Antigravity
context_required:
  - InstaAddict/core/navigation.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/core/views.py
  - test/test_tuning_and_operational_fixes.py
files_affected:
  - InstaAddict/core/navigation.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/core/views.py
  - test/test_tuning_and_operational_fixes.py
tokens_est: 2800
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-24
completed: '2026-09-24'
override_reason:
---

# Route-064: Hashtag Navigation Verification & Self-Healing Escape Hardening

## Objectives
1. **CO-073**: Harden `nav_to_hashtag_or_place()` in `InstaAddict/core/navigation.py`:
   - Calculate center-point coordinates from the target thumbnail bounds and use crisp touch events (`device.deviceV2.click(x, y)`), falling back to `.click()`.
   - Implement a 2-attempt tap retry loop verifying `OpenedPostView(device).is_post_opened()`.
   - Expand `OpenedPostView.is_post_opened()` in `InstaAddict/core/views.py` to recognize modern Reels/Clips viewers (`ROOT_CLIPS_LAYOUT`, `CLIPS_VIEWER_CONTAINER`, `CLIPS_VIDEO_CONTAINER`).
   - Add `_getFirstImageView()` to `HashTagView` and `PlacesView` in `views.py` with backward-compatible alias.
2. **CO-074**: Implement `nr_consecutive_unidentifiable` circuit breaker in `handle_sources.py:handle_posts()`:
   - Track consecutive posts where no valid username/author is resolved.
   - Enforce a strict threshold of 5 consecutive unidentifiable posts.
   - Upon breach: log warning, record skip in `HashtagManager.record_hashtag_result(target, posts_found=False)`, and break out of the while loop to advance to the next hashtag/source.
   - Record `_record_source_skip(session_state, "UNIDENTIFIABLE")` on unidentifiable posts so telemetry and DogfoodOptimizer have full visibility.
   - Reset counter to 0 whenever a valid author is resolved.
3. **CO-075**: Self-Healing Watchdog & Sentinel Hardening:
   - Condition `record_heartbeat()` in `handle_posts()` on verified author discovery or interaction success, preventing heartbeat spoofing during empty loops.
   - Wire `UniversalActions.check_micro_stall(device, context=...)` into `handle_posts()`.
   - If `dismiss_peek_if_open()` dismisses an overlay, assert `is_post_opened()`; if the UI fell back to the grid, break or retry cleanly instead of swiping the grid.
4. Add comprehensive unit tests in `test/test_tuning_and_operational_fixes.py` covering all new verification and circuit-breaking paths.
5. Verify 100% green test suite (407+ tests passing) and pass all ACP CI fast gates.

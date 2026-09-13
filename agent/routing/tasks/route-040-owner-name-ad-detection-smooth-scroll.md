---
id: route-040
title: Fix Owner Name Resolution, Eliminate False Ad Detection, and Implement Smooth Scrolling
task_type: python-code-fix
milestone: M2
complexity: medium
executor: antigravity
context_required:
  - agent/reports/audit-037-owner-name-ad-detection-and-scroll-jerk.md
files_affected:
  - InstaAddict/core/resources.py
  - InstaAddict/core/views.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/core/device_facade.py
  - test/test_owner_ad_detection_and_scroll.py
tokens_est: 8000
tokens_actual:
cost_est_usd: 0.00
cost_actual_usd:
created: 2026-09-13
completed: 2026-09-13
override_reason:
---

## Task Description

Resolve hashtag post browsing failures:
1. Support multi-tier author name extraction in `_post_owner` covering both regular feed posts and Reels/Clips posts (`CLIPS_AUTHOR_USERNAME`, `CLIPS_AUTHOR_PROFILE_PIC`, `ROW_FEED_PHOTO_PROFILE_NAME`, `ROW_FEED_PROFILE_HEADER`).
2. Eliminate false-positive advertisement detection: never set `is_ad = True` when an owner name is unresolvable; only flag genuine advertisements with verified ad indicators.
3. Replace jerky multi-swipe sequences (caused by redundant `HALF_PHOTO` swipes and obsolete gap view retries) with a single, smooth, calculated swipe.
4. Add comprehensive unit tests and verify 100% pass rate.

## Acceptance Criteria

- [x] `_post_owner` correctly resolves usernames from Reels and feed posts
- [x] Posts with missing or unresolvable owner names are NEVER marked as ads
- [x] Jerky 3x `HALF_PHOTO` loop removed from `swipe_to_fit_posts`
- [x] Reels mode performs a clean, single vertical swipe
- [x] Redundant `HALF_PHOTO` in `handle_sources.py:768` removed
- [x] Comprehensive unit test suite added and passing 100%

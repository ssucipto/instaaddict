---
id: route-052
title: Engagement Pipeline Restoration — Follows, Unfollows, and Comments Architecture & Selector Hardening
task_type: bugfix
milestone: M7
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-077-follows-unfollows-comments-zero-metrics-investigation.md
  - agent/memory/audit-carryovers.md
  - InstaAddict/core/views.py
  - InstaAddict/core/interaction.py
  - InstaAddict/core/filter.py
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/plugins/action_unfollow_followers.py
files_affected:
  - InstaAddict/core/views.py
  - InstaAddict/core/interaction.py
  - InstaAddict/core/filter.py
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/plugins/action_unfollow_followers.py
  - test/test_engagement_pipeline.py
tokens_est: 14000
tokens_actual:
cost_est_usd: 0.00
cost_actual_usd:
created: 2026-09-19
completed: 2026-09-19
override_reason:
---

## Task Description

Address all findings from Audit-077 and resolve carryovers CO-059, CO-060, and CO-061 to completely eliminate the zero metrics anomaly for follows, unfollows, and comments across all automation modes:
1. **Follows**:
   - Decouple `clickable=True` constraint on TextView nodes in `ProfileView.getFollowButton()` and `interaction._follow()` for IG v446+ compatibility.
   - Eliminate false-positive `SkipReason.NOT_LOADED` rejections in `Filter.check_profile()`.
2. **Comments**:
   - In `_comment()`, eliminate destructive downward swipe when `media_type == MediaType.REEL`.
   - Add multi-tier comment button locators matching Reels action bar (`comment_button`, `clips_comment_button`, description `"Comment"`).
   - Implement multi-tier comment confirmation (description regex, edittext cleared/placeholder, post button dismissal) replacing fragile hardcoded English string matcher.
   - Provide safe fallback comments and graceful support for `comments_list.txt` without section headers.
3. **Unfollows**:
   - Ensure `ProfileView.navigateToFollowing()` returns boolean `True` when following list opens directly without tab bar.
   - Replace rigid index traversal (`item.child(index=1)...`) with resilient username discovery across Following rows.
   - Support multi-tier unfollow buttons and confirmation sheet dialogs without strict `clickable=True` or hardcoded `index=2`.
4. **Verification**:
   - Create comprehensive unit test suite `test/test_engagement_pipeline.py` verifying follow button detection, comment submission and verification, and unfollow action flow.
   - Ensure 100% test pass rate with 0 regressions.

## Acceptance Criteria

- [ ] `ProfileView.getFollowButton()` detects Follow, Following, and Follow Back buttons regardless of whether `clickable` is set on the TextView or parent container.
- [ ] `Filter.check_profile()` correctly identifies loaded profiles and does not reject them with `SkipReason.NOT_LOADED`.
- [ ] `_follow()` successfully finds and clicks Follow buttons without strict `clickable=True` failure.
- [ ] `_comment()` does not execute downward swipe on `MediaType.REEL`.
- [ ] `_comment()` reliably opens the comment sheet on Reels using modern resource IDs and description matchers.
- [ ] `_comment()` increments `totalComments` using multi-tier confirmation (regex, cleared box, or button transition).
- [ ] `load_random_comment()` returns valid comments even if `comments_list.txt` lacks `%PHOTO` headers, and provides defaults if file is missing.
- [ ] `ProfileView.navigateToFollowing()` returns `True` when Following list or search bar is visible.
- [ ] `action_unfollow_followers.py` correctly parses usernames from following list rows without index assumptions.
- [ ] Unfollow confirmation dialogs detect the "Unfollow" button across both old and modern bottom sheets.
- [ ] Comprehensive unit test suite `test/test_engagement_pipeline.py` passes 100%.
- [ ] All unit tests in the project pass with 0 errors and 0 lint violations.

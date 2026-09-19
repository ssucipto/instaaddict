---
id: route-059
title: Implement Post-View Commenting in handle_posts and Unblock Feed and Hashtag Follows/Comments
task_type: bugfix
milestone: null
complexity: medium
executor: Antigravity
context_required:
  - agent/reports/audit-089-follows-and-comments-deep-dive-investigation.md
  - InstaAddict/core/handle_sources.py
  - InstaAddict/core/interaction.py
  - InstaAddict/core/filter.py
  - accounts/lolatheozjack/filters.yml
  - accounts/lolatheozjack/config.yml
files_affected:
  - InstaAddict/core/handle_sources.py
  - accounts/lolatheozjack/filters.yml
  - accounts/lolatheozjack/config.yml
  - test/test_post_view_commenting.py
tokens_est: 3500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: '2026-09-19'
completed: '2026-09-19'
override_reason:
---

# Route-059: Implement Post-View Commenting in handle_posts and Unblock Follows/Comments

## Context & Objectives
In live runs (`logs/lolatheozjack.log`), Session #1 and #2 executed 26 likes but **0 follows** and **0 comments**.
Audit #089 diagnosed that `handle_posts` in `InstaAddict/core/handle_sources.py` contains zero post-commenting logic. Even though `comment_feed: true` and `comment-percentage: 15-30` are configured, `_comment()` is never called in `handle_posts`. For `feed`, profile navigation is also intentionally skipped, causing feed comments to be completely dead code.

Furthermore, on hashtag feeds, 20/21 opened profiles were skipped due to existing followings and high follower counts, and Session #2 terminated prematurely before `interact-reels` could run because `end-if-likes-limit-reached: true`.

## Key Changes
1. **Post-View Commenting in `handle_posts` (`handle_sources.py`)**:
   - In `handle_posts`, after a post is liked (or checked as already liked):
   - Evaluate `profile_filter.can_comment(current_job)`
   - Check `comment_percentage > 0` and `session_state.check_limit(Limit.COMMENTS, output=False) is not True`
   - Evaluate probability via `random.randint(1, 100) <= comment_pct`
   - If triggered: call `_comment(device, my_username, 100, args, session_state, media_type)`
   - On success: `_comment()` increments `session_state.totalComments += 1` and records telemetry
2. **Filter & Config Optimization**:
   - Verify `accounts/lolatheozjack/filters.yml` has `comment_feed: true`, `skip_following: false`, `skip_follower: false`
   - Verify `accounts/lolatheozjack/config.yml` has `end-if-likes-limit-reached: false` and `blogger-followers: [ perthdogs, dogsofperth, jackrussellmoments ]`
3. **Automated Verification**:
   - Create unit tests in `test/test_post_view_commenting.py` verifying feed commenting, hashtag post commenting, limit enforcement, and error resilience
   - Run 100% full regression test suite (292 tests green)
   - Enforce 0 flake8 lint violations

## Acceptance Criteria
- [x] `handle_posts` executes `_comment` on target posts according to `comment_percentage` and filter permissibility.
- [x] Post-view commenting works for both `current_job == "feed"` and hashtag/place feeds.
- [x] Session limits on comments are strictly respected.
- [x] Unit test suite created in `test/test_post_view_commenting.py` and passing 100%.
- [x] Full regression test suite passing with zero failures (292/292 passed).
- [x] Zero flake8 linting violations on modified code.

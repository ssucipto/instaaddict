---
id: route-054
title: Unfollow Optimization, Local Followers Cache, and Directional Sorting
task_type: performance-optimization
milestone: M7
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-082-unfollow-optimization-and-modern-bot-capabilities.md
  - InstaAddict/plugins/action_unfollow_followers.py
  - InstaAddict/core/storage.py
  - InstaAddict/core/views.py
  - InstaAddict/core/session_state.py
files_affected:
  - InstaAddict/core/storage.py
  - InstaAddict/plugins/action_unfollow_followers.py
  - InstaAddict/core/views.py
  - InstaAddict/core/resources.py
  - test/test_unfollow_optimization.py
tokens_est: 16000
tokens_actual:
cost_est_usd: 0.00
cost_actual_usd:
created: 2026-09-19
completed: 2026-09-19
override_reason:
---

## Task Description

Implement comprehensive architectural optimizations for the unfollow task as documented in `audit-082`:
1. **Persistent Local Followers Cache (`followers_cache.json`) in `Storage`**:
   - Store known followers in a persistent JSON cache (`accounts/<username>/followers_cache.json`) with atomic writes (`atomic_write`).
   - Provide $O(1)$ set membership checks `is_follower(username)`.
   - Track `last_followers_count` and timestamp of last harvest.
2. **Follower Count Delta Guard**:
   - Before scanning the user's Followers list, compare current `session_state.my_followers_count` against `storage.last_followers_count`.
   - If count is unchanged ($\Delta = 0$) and cache exists, bypass Followers list harvest entirely.
   - If count increased or cache is empty, perform a fast-harvest of the top viewports of the Followers list (newest followers are at the top).
3. **Elimination of N-Profile Following List Traversal Anti-Pattern**:
   - In `action_unfollow_followers.py`, replace `check_is_follower()` nested following-list traversal:
     - Check 1: In-memory `storage.is_follower(username)` (instant $O(1)$).
     - Check 2 (Fallback on profile visit): Check for native `"Follows you"` subtitle tag (`textMatches="(?i)^Follows you$"` or `descriptionMatches="(?i)^Follows you$"`) directly on the profile header in `ProfileView`. Never open the candidate's Following list.
4. **Directional Sorting by "Latest" (Newest Followings First)**:
   - Add option and default behavior to sort by "Date followed: Latest" so accounts followed 3–7 days ago (past `unfollow_delay`) are evaluated at the top of the list, achieving quotas within 30–50 rows rather than deep scrolling through thousands of old followings.
5. **Testing & Quality**:
   - Create comprehensive unit test suite in `test/test_unfollow_optimization.py`.
   - Verify 0 regressions across all 245 existing tests.

---
id: route-058
title: Remediate 0-Follows and 0-Comments via Audit-088 Findings (Filters, Config, Reels Decoupling, Pytest Configuration)
task_type: bugfix
milestone: null
complexity: medium
executor: Antigravity
context_required:
  - agent/reports/audit-088-follows-and-comments-log-investigation.md
  - accounts/lolatheozjack/filters.yml
  - accounts/lolatheozjack/config.yml
  - InstaAddict/plugins/interact_reels.py
  - pyproject.toml
files_affected:
  - accounts/lolatheozjack/filters.yml
  - accounts/lolatheozjack/config.yml
  - InstaAddict/plugins/interact_reels.py
  - pyproject.toml
  - test/test_reels_engagement_decoupling.py
tokens_est: 3500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: '2026-09-19'
completed: '2026-09-19'
override_reason:
---

# Route-058: Remediate 0-Follows and 0-Comments via Audit-088 Findings

## Context & Objectives
In live production runs (`logs/lolatheozjack.log`), Session #1 and #2 resulted in 26 likes, 0 follows, and 0 comments.
Audit #088 isolated 5 root causes:
1. **R-01**: `comment_feed: false` in `accounts/lolatheozjack/filters.yml` explicitly disabled commenting on home feed posts.
2. **R-02**: `end-if-likes-limit-reached: true` in `accounts/lolatheozjack/config.yml` prematurely terminated Session #2 upon reaching 21 likes on hashtag posts, aborting before `interact-reels` or other jobs could run.
3. **R-03**: In `interact_reels.py`, double-tap likes and creator follows are slaved inside `if comment_text:`. If Gemini Vision is safety-blocked, times out, or evaluates empty, liking and following are discarded. Liking and following should execute independently, and non-empty fallback comments should be used when Vision AI is unavailable or blocked on target reels.
4. **R-04**: `skip_following: true` and `skip_follower: true` in `filters.yml` skipped 100% of candidate profiles on hashtag feeds because community tags are saturated with accounts Lola already follows or who follow Lola. Set `skip_following: false` so friends' posts can be liked and commented on (while `can_follow=False` prevents duplicate follows), and add fresh audience discovery sources (`blogger-followers`) in `config.yml`.
5. **R-05**: Configure `[tool.pytest.ini_options]` with `testpaths = ["test"]` in `pyproject.toml` to prevent pytest from attempting to collect scratch and manual ad-hoc scripts.

## Acceptance Criteria
- `accounts/lolatheozjack/filters.yml` updated with `comment_feed: true` and `skip_following: false`.
- `accounts/lolatheozjack/config.yml` updated with `end-if-likes-limit-reached: false` and blogger-followers sources.
- `interact_reels.py` updated to decouple liking/following from comment presence and provide fallback comment safety.
- `pyproject.toml` updated with `testpaths = ["test"]`.
- `test/test_reels_engagement_decoupling.py` created and passing 100%.
- Full regression test suite passing with 0 failures.
- Zero flake8 linting violations.

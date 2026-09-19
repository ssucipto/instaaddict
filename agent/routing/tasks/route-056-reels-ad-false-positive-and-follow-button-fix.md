---
id: route-056
title: Fix Reels False Ad Classification, Inline Follow Button Locator, and Post-View Comment Lifecycle
task_type: bugfix
milestone: null
complexity: medium
executor: Antigravity
context_required:
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/interaction.py
  - test/test_reels_ad_and_follow_fix.py
files_affected:
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/interaction.py
  - accounts/lolatheozjack/config.yml
  - test/test_reels_ad_and_follow_fix.py
tokens_est: 1800
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: '2026-09-19'
completed: '2026-09-19'
override_reason:
---

# Route-056: Fix Reels False Ad Classification, Inline Follow Button Locator, and Post-View Comment Lifecycle

## Context & Objectives
In live runs, the bot achieved 0 follows and 0 comments due to:
1. False-positive ad classification in `interact_reels.py` matching "Subscribe" and recycled off-screen views, flinging away 100% of organic reels.
2. Premature `device.back()` calls in `interaction.py` lines 361 and 372 returning to the profile grid before `_comment()` runs.
3. Missing `inline_follow_button` in `interact_reels.py` follow button selector.
4. Probabilistic target drops via `interact-percentage: 60-80` in `config.yml`.

## Acceptance Criteria
1. `ad_cta_regex` in `interact_reels.py` does not match "Subscribe".
2. `ad_button` in `interact_reels.py` verifies vertical bounds (`top > height * 0.4`) and banner width before classifying as an ad.
3. Reels follow button selector in `interact_reels.py` includes `.*inline_follow_button.*`.
4. `device.back()` in `interaction.py` executes after post comments, ensuring the post remains open while `_comment()` evaluates and executes.
5. All 273+ existing tests pass with 0 regressions.
6. 100% clean flake8 linting.

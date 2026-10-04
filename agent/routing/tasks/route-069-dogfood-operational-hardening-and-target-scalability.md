---
id: route-069
title: "Dogfood Operational Hardening, Target Pool Scalability, and Navigation Resilience"
task_type: full-implementation
milestone: M7
complexity: high
executor: Antigravity
context_required:
  - accounts/lolatheozjack/config.yml
  - InstaAddict/core/dogfood.py
  - InstaAddict/core/views.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/plugins/interact_hashtag_posts.py
  - InstaAddict/plugins/action_unfollow_followers.py
  - InstaAddict/core/watchdog.py
  - agent/memory/audit-carryovers.md
files_affected:
  - accounts/lolatheozjack/config.yml
  - InstaAddict/core/dogfood.py
  - InstaAddict/core/views.py
  - InstaAddict/core/handle_sources.py
  - InstaAddict/plugins/interact_hashtag_posts.py
  - InstaAddict/plugins/action_unfollow_followers.py
  - test/test_dogfood_operational_hardening.py
tokens_est: 2800
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-10-05
completed: 2026-10-05
override_reason:
---

# Route 069: Dogfood Operational Hardening, Target Pool Scalability, and Navigation Resilience

## Objectives & Acceptance Criteria
1. **Target Pool Replenishment (CO-119)**:
   - Expand `blogger-followers` in `accounts/lolatheozjack/config.yml` from 20 to 50+ niche canine accounts.
   - Expand `hashtag-posts-recent` from 10 to 25+ relevant tags.
   - Enhance `DogfoodOptimizer` in `dogfood.py` to detect `COOLDOWN` skip rate > 40% and recommend dynamic replenishment.
2. **Profile & Followers Progressive Navigation (CO-120)**:
   - In `views.py:ProfileView.navigateToFollowers()`, implement progressive polling (up to 15s) for `followers_button` to withstand P95=114s profile tail latency.
3. **Hashtag Engine Inactivity Circuit Breaker (CO-121)**:
   - Support v447+ Top/Recent-Top hashtag tabs in `interact_hashtag_posts.py`.
   - Add 3-strike zero-yield fast-skip in `handle_sources.py` when a hashtag yields no interactable posts or triggers repeated grid traps.
4. **Unfollow Sorting & Non-Bot Saturation Guard (CO-122)**:
   - Broaden sorting button locators in `action_unfollow_followers.py` to match modern IG v447+ variants.
   - Enforce 30-consecutive-skip circuit breaker on cached non-bot followings to prevent unproductive 1128s idle loops.
5. **Subscreen Escape Foreground Safeguard (CO-123)**:
   - Check package state before back presses during deep subscreen recovery to prevent popping out to Android launcher.
6. **Watchdog Heartbeat Synchronization (CO-124)**:
   - Feed soft heartbeats during profile loading and pagination in `handle_sources.py`.
7. **Comprehensive Unit Test Suite**:
   - Author `test/test_dogfood_operational_hardening.py` covering all 6 components with 100% pass rate.
   - Zero regressions across the entire test suite (496+ tests passing).

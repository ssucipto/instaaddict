---
id: route-057
title: Fix Session State Follow Dict Type Invariant, Range-Safe Percentage Parsing, and Already-Liked Commenting
task_type: bugfix
milestone: null
complexity: medium
executor: Antigravity
context_required:
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/interaction.py
  - agent/reports/audit-087-implementation-gaps-inconsistencies-shortcuts.md
  - agent/reports/review-049-code-quality.md
files_affected:
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/interaction.py
  - test/test_follows_and_comments_robustness.py
tokens_est: 2200
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: '2026-09-19'
completed: '2026-09-19'
override_reason:
---

# Route-057: Fix Session State Follow Dict Type Invariant, Range-Safe Percentage Parsing, and Already-Liked Commenting

## Context & Objectives
Address all 5 findings from Audit #087 and Review #049:
1. **F-01**: Remove integer reassignment to `sessions[-1].totalFollowed` in `interact_reels.py`, preserving `totalFollowed` as a `dict[str, int]` managed via `add_interaction()`.
2. **F-02**: Parse `follow_percentage` and `evaluate_percentage` in `interact_reels.py` using `get_value()`, preventing `ValueError` crashes on range expressions (`"30-40"`).
3. **F-03**: Allow commenting on open posts in `interaction.py` even if `already_liked == True`.
4. **F-04**: Guard `can_comment()` in `interaction.py` against `profile_filter is None`.
5. **F-05**: Ensure `load_random_comment()` always returns a non-empty string fallback from `DEFAULT_COMMENTS`.

## Acceptance Criteria
- `test_follows_and_comments_robustness.py` created and passing 100%.
- Full regression suite (279+ tests) passing with 0 failures.
- Zero flake8 linting violations.

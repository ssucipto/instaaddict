---
id: route-055
title: Restore Follows and Comments Mechanics, Add Reels Follow, and Vision AI Subtle Aussie Voice
task_type: feature-enhancement
milestone: M7
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-085-follows-comments-and-vision-ai-audit.md
  - InstaAddict/core/gemini_vision.py
  - InstaAddict/core/filter.py
  - InstaAddict/core/interaction.py
  - InstaAddict/plugins/interact_reels.py
  - accounts/lolatheozjack/filters.yml
  - accounts/lolatheozjack/config.yml
files_affected:
  - InstaAddict/core/gemini_vision.py
  - InstaAddict/core/filter.py
  - InstaAddict/core/interaction.py
  - InstaAddict/plugins/interact_reels.py
  - accounts/lolatheozjack/filters.yml
  - accounts/lolatheozjack/config.yml
  - test/test_follows_and_comments_remediation.py
tokens_est: 18000
tokens_actual:
cost_est_usd: 0.00
cost_actual_usd:
created: 2026-09-19
completed: 2026-09-19
override_reason:
---

## Task Description

Remediate zero-follow and zero-comment bottlenecks, eliminate em-dashes and AI-like speech patterns in Vision AI comments, add Reel author follow capability, and fix hashtag saturation:

1. **Vision AI Sanitizer & Prompt Tuning (`InstaAddict/core/gemini_vision.py`)**:
   - In `_sanitize_response(text)`: Replace all em-dashes (`—`, `–`) with commas or hyphens and strip AI markers.
   - In `get_vision_comment()` and `evaluate_and_comment_reel()`: Ban em-dashes, forbid AI jargon/enthusiasm, and instruct a natural voice with subtle Aussie flavour (*reckon*, *heaps*, *ripper*, *mate*, *cheers*, *keen*), punchy in 3-6 words.
   - In `get_vision_caption()`: Apply matching anti-em-dash and authentic persona constraints.

2. **Comment Permissibility Heuristic (`InstaAddict/core/filter.py`)**:
   - In `can_comment(self, current_mode)`: Default `comment_<mode>` check to `True` (unless explicitly configured as `False` in `filters.yml`).

3. **Subtle Aussie Fallback Comments (`InstaAddict/core/interaction.py`)**:
   - Update `DEFAULT_COMMENTS` in `load_random_comment()` to authentic, subtle Aussie dog-friendly comments with no em-dashes.

4. **Reels Follow Interaction (`InstaAddict/plugins/interact_reels.py`)**:
   - Add native Follow action for matching Reels targeting `com.instagram.android:id/clips_follow_button` or button with text/desc "Follow".
   - Support configurable `evaluate_percentage` defaulting to 70% instead of 25%.

5. **Account Configuration Updates**:
   - Add explicit `comment_*` permissions in `accounts/lolatheozjack/filters.yml`.
   - Update `accounts/lolatheozjack/config.yml` with `evaluate-percentage: '70'` and blogger follower sources.

6. **Verification**:
   - Create unit tests in `test/test_follows_and_comments_remediation.py`.
   - Ensure 100% pass rate across entire repository test suite.

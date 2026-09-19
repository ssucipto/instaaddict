---
id: route-053
title: Reels Caption Extraction Multi-Tier Resiliency & TUI [CTRL] Shortcuts Migration
task_type: bugfix
milestone: M7
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-079-reels-caption-extraction-and-ctrl-shortcuts.md
  - InstaAddict/core/views.py
  - InstaAddict/core/tui.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/utils.py
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/handle_sources.py
files_affected:
  - InstaAddict/core/views.py
  - InstaAddict/core/tui.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/utils.py
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/handle_sources.py
  - test/test_reels_caption_and_ctrl_shortcuts.py
tokens_est: 15000
tokens_actual:
cost_est_usd: 0.00
cost_actual_usd:
created: 2026-09-19
completed: 2026-09-19
override_reason:
---

## Task Description

Address all findings from Audit-079 and ensure zero regressions across the codebase:
1. **Reels Caption Extraction Resilience**:
   - In `PostsViewList._check_if_last_post()`, resolve the root cause where `clips_caption` exists as a `ViewGroup` container with empty text/contentDescription.
   - Implement multi-tier caption discovery:
     - Tier 1: Direct text/desc on `clips_caption`.
     - Tier 2: Child `TextView` querying inside `clips_caption` with multi-item aggregation.
     - Tier 3: Alternative Reels caption locators (`clips_caption_title`, `clips_caption_text`, `video_caption`, `clips_viewer_caption`, `reel_viewer_title`, `expandable_text_component`).
     - Tier 4: XML hierarchy traversal parser extracting caption nodes within the Reel viewport while stripping trailing `"...more"` or `"more"`.
     - Tier 5: Fallback logging only when all tiers are exhausted.
2. **TUI [CTRL] Shortcuts Migration**:
   - Update `KeyboardListenerThread._handle_key()` in `InstaAddict/core/tui.py` to support ASCII control characters:
     - `CTRL+S`: `\x13` (byte 19), with fallbacks for `'s'`, `'S'`, `'n'`, `'N'`
     - `CTRL+U`: `\x15` (byte 21), with fallbacks for `'u'`, `'U'`
     - `CTRL+D`: `\x04` (byte 4), with fallbacks for `'d'`, `'D'`
   - Update `DashboardManager.trigger_upload_request()`, `trigger_skip_task()`, and `trigger_debug_toggle()`:
     - `trigger_debug_toggle()` must dynamically toggle the root logger effective level between `DEBUG` and `INFO`.
   - Add `is_upload_requested()` to `DashboardState` for non-destructive polling.
   - Integrate `is_upload_requested()` checks into:
     - `wait_for_next_session()` in `InstaAddict/core/utils.py` (breaks inter-session sleep immediately).
     - `interact_reels.py` and `handle_sources.py` (breaks interaction loops to process upload immediately).
     - `bot_flow.py` (processes upload immediately when triggered).
   - Update `_render_footer()` to display `[Ctrl+S] Skip | [Ctrl+U] Upload | [Ctrl+D] Debug | [Ctrl+C] Stop`.
3. **Automated Verification**:
   - Create unit test suite `test/test_reels_caption_and_ctrl_shortcuts.py` verifying:
     - Child TextView caption extraction inside `clips_caption_component`.
     - Alternative selector caption extraction.
     - XML hierarchy dump extraction with `"...more"` stripping.
     - Fallback behavior when a Reel genuinely has no caption.
     - `KeyboardListenerThread` handling of `\x13` (CTRL+S), `\x15` (CTRL+U), `\x04` (CTRL+D), and character fallbacks.
     - `DashboardState` upload request lifecycle and `trigger_debug_toggle` logger level switching.
     - Responsive wakeup in `wait_for_next_session`.

## Acceptance Criteria

- [ ] `_check_if_last_post()` successfully extracts the caption from child `TextView`s when `CLIPS_CAPTION_COMPONENT` is a ViewGroup with empty direct text.
- [ ] `_check_if_last_post()` extracts captions using alternative Reels selectors (`video_caption`, `clips_caption_text`, `expandable_text_component`).
- [ ] `_check_if_last_post()` parses XML hierarchy for Reel caption nodes when direct element queries fail.
- [ ] Trailing `"...more"` is cleanly removed from extracted Reels captions.
- [ ] `logger.info("This Reel post hasn't a caption description...")` is only logged when all extraction tiers find no text.
- [ ] `KeyboardListenerThread` handles `b'\x13'` / `'\x13'` (`CTRL+S`) to trigger skip task.
- [ ] `KeyboardListenerThread` handles `b'\x15'` / `'\x15'` (`CTRL+U`) to trigger on-demand upload.
- [ ] `KeyboardListenerThread` handles `b'\x04'` / `'\x04'` (`CTRL+D`) to toggle debug logging level.
- [ ] Pressing `[CTRL+U]` during inter-session wait immediately wakes up the bot to execute upload.
- [ ] Pressing `[CTRL+U]` during interaction loops cleanly exits the loop to execute upload without waiting for entire job completion.
- [ ] TUI footer reflects `[Ctrl+S] Skip | [Ctrl+U] Upload | [Ctrl+D] Debug | [Ctrl+C] Stop`.
- [ ] All new tests pass, baseline test suite passes 100% green, and `flake8` is clean.

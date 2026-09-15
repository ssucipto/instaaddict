---
id: route-043
title: Runtime Errors, Argument Collisions, and Navigation Locator Remediation
task_type: bug-fix-complex
milestone: milestone-8-auto-upload-pipeline
complexity: medium
executor: Antigravity
context_required:
  - agent/reports/audit-045-runtime-errors-and-locator-investigation.md
  - agent/memory/audit-carryovers.md
files_affected:
  - InstaAddict/plugins/core_arguments.py
  - InstaAddict/core/config.py
  - InstaAddict/core/decorators.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/views.py
  - InstaAddict/core/resources.py
  - InstaAddict/plugins/data_analytics.py
tokens_est: 7500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-14
completed: 2026-09-14
override_reason:
---

## Description
Remediate all 6 findings from Audit Report #045:
1. **AUD-045-01**: Remove duplicate `--reels-topic` definition from `core_arguments.py`, add collision guard (`if arg_name in self.parser._option_string_actions: continue`) in `config.py`, and accurately report argument errors in logs.
2. **AUD-045-02**: Wrap `input("")` in `decorators.py` with `except (KeyboardInterrupt, EOFError):` to prevent unhandled fatal crashes when stdin is closed.
3. **AUD-045-03**: Add `error: bool = True` to `_getActionBarTitleBtn` and `getUsername` in `views.py`. Update speculative pre-navigation check in `bot_flow.py` to use `error=False` to eliminate false-alarm errors.
4. **AUD-045-04**: Define `FEED_TAB`, `SEARCH_TAB`, `CLIPS_TAB`, `DIRECT_TAB`, and `PROFILE_TAB` in `resources.py` and update `TabBarView._navigateTo()` to prioritize these resource IDs before falling back to content descriptions.
5. **AUD-045-05**: Fix string concatenation in `data_analytics.py` using `os.path.join(storage.report_path, ...)` to generate reports cleanly in `accounts/<user>/reports/`.
6. **AUD-045-06**: In `bot_flow.py` navigation recovery loop, tap `ResourceID.ACTION_BAR_BUTTON_BACK` directly when present to exit active search queries without multi-second delays.

## Acceptance Criteria
- [ ] No `conflicting option string` error occurs on startup.
- [ ] `EOFError` is safely trapped in `decorators.py` and halts execution cleanly.
- [ ] `profile_view.getUsername(error=False)` suppresses false-alarm errors on non-profile screens.
- [ ] Tab bar navigation resolves modern resource IDs on Instagram v446+.
- [ ] Data analytics report filenames are properly formed with `os.path.join`.
- [ ] All existing unit tests pass, plus new tests covering Audit #045 fixes.
- [ ] Carryover CO-014 status updated to fixed.

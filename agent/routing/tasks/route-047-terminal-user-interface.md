---
id: route-047
title: Modern Terminal User Interface (TUI) & Live Dashboard
task_type: feature
milestone: M10
complexity: medium
executor: antigravity
context_required:
  - agent/design/tui-dashboard.md
  - agent/milestones/milestone-10-terminal-user-interface.md
  - InstaAddict/core/session_state.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/log.py
files_affected:
  - InstaAddict/core/tui.py
  - InstaAddict/core/log.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/utils.py
  - requirements.txt
  - pyproject.toml
  - test/test_tui_dashboard.py
tokens_est: 4000
tokens_actual: 3800
cost_est_usd: 0.015
cost_actual_usd: 0.014
created: 2026-09-17
completed: 2026-09-17
override_reason:
---

## Objective
Implement an interactive, high-performance terminal user interface and live dashboard for InstaAddict using `rich`. The interface will present real-time session progress bars against safety limits, active job and target context, and a live rolling log stream, with automatic headless fallbacks.

## Acceptance Criteria
- [x] Create `InstaAddict/core/tui.py` with `DashboardState`, `TuiLogHandler`, and `DashboardManager`.
- [x] Render dual-column responsive layout: Header banner, Stats & Progress table, Activity context, Rolling logs window, and Footer status.
- [x] Route logging through `TuiLogHandler` when TUI is active, preventing stdout clobbering.
- [x] Support `--tui` and `--no-tui` CLI options with automatic TTY detection.
- [x] Update `requirements.txt` and `pyproject.toml` with `rich>=13.0.0`.
- [x] Provide 100% passing unit tests in `test/test_tui_dashboard.py`.
- [x] Maintain 0 regressions across all existing pytest tests (166 passed).

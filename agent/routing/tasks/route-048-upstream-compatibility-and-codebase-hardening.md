---
id: route-048
title: Upstream Compatibility Alignment & Codebase Gap Remediation
task_type: bugfix
milestone: M10
complexity: medium
executor: antigravity
context_required:
  - agent/reports/audit-062-upstream-repo-improvements-and-compatibility.md
  - agent/reports/audit-063-codebase-gaps-bare-excepts-and-quality-hardening.md
  - InstaAddict/core/interaction.py
  - InstaAddict/core/download_from_github.py
  - InstaAddict/core/filter.py
files_affected:
  - InstaAddict/__init__.py
  - InstaAddict/version.py
  - pyproject.toml
  - InstaAddict/core/interaction.py
  - InstaAddict/core/download_from_github.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/filter.py
  - InstaAddict/core/gemini_vision.py
  - InstaAddict/core/tui.py
  - test/test_tui_dashboard.py
  - test/test_runtime_hardening.py
  - test/test_unicode_sanitizer.py
tokens_est: 3500
tokens_actual: 3200
cost_est_usd: 0.012
cost_actual_usd: 0.011
created: 2026-09-18
completed: 2026-09-18
override_reason:
---

## Objective
Harmonize fork with verified upstream releases (Instagram v447.0.0.55.81), eliminate bare `except:` anti-patterns, enforce explicit subprocess timeouts on all ADB interactions, and achieve 100% clean linter and zero-regression automated test passes.

## Acceptance Criteria
- [x] Port tested Instagram version `447.0.0.55.81` into `InstaAddict/__init__.py`.
- [x] Synchronize `pyproject.toml` dependencies with `requirements.txt`.
- [x] Remediate bare `except:` statements in `interaction.py` and `download_from_github.py`.
- [x] Add explicit `timeout=5` and module-level import on ghost-typing ADB keyevent 62 in `interaction.py`.
- [x] Clean unused imports across core modules and test suites without breaking test mocks.
- [x] Verify zero flake8 violations on `F401, F811, F821, E722`.
- [x] Verify all 168 tests pass in automated regression test suite (`pytest`).

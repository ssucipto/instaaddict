---
id: route-063
title: Crash Remediation, Non-Fatal EmptyList Recovery, and Dogfood Optimizer Modernization
task_type: bugfix
milestone: M7
complexity: medium
executor: Antigravity
context_required:
  - InstaAddict/core/views.py
  - InstaAddict/core/decorators.py
  - InstaAddict/core/dogfood.py
  - test/test_tuning_and_operational_fixes.py
files_affected:
  - InstaAddict/core/views.py
  - InstaAddict/core/decorators.py
  - InstaAddict/core/dogfood.py
  - test/test_tuning_and_operational_fixes.py
tokens_est: 2500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-23
completed: 2026-09-23
override_reason:
---

# Route-063: Crash Remediation & Dogfood Optimizer Modernization

## Objectives
1. **CO-067**: Harden `HomeView.navigateToSearch()` and `SearchView.navigate_to_target()` in `InstaAddict/core/views.py` against transient `JsonRpcError` and `UiObjectNotFoundError` on search button clicks and input focus.
2. **CO-068**: Remove `EmptyList` from the `restart()` tuple in `InstaAddict/core/decorators.py:89`. Add dedicated non-fatal `except EmptyList:` handler in `@run_safely` that advances to the next task without killing Instagram, incrementing `totalCrashes`, or dumping crash zips.
3. **CO-069**: Modernize `DogfoodOptimizer` in `InstaAddict/core/dogfood.py`:
   - Introduce a configurable sliding session window (`window_sessions=5`) to evaluate active bot performance without distortion from historical baggage.
   - Parse distinct traceback blocks and filter logs by session window timestamp in `_analyze_error_log()`.
   - Eradicate `delay-mean` placebo recommendations for locator errors and API quotas.
4. Add comprehensive unit tests in `test/test_tuning_and_operational_fixes.py` verifying all hardened error paths and sliding window calculations.
5. Verify 100% green test suite (374+ tests passing) and run `/acp-ci --fast`.

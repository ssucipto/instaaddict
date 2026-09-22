---
id: route-060
title: Implement Subscreen Auto-Escape, Defensive HomeView Navigation, and Restart Resilience
task_type: bugfix
milestone: null
complexity: medium
executor: Antigravity
context_required:
  - agent/reports/audit-092-uiautomator2-tabbar-crash-investigation.md
  - agent/reports/audit-093-pre-implementation-gaps-and-dogfooding.md
  - InstaAddict/core/views.py
  - InstaAddict/core/decorators.py
  - InstaAddict/core/utils.py
  - InstaAddict/core/session_state.py
  - InstaAddict/core/dogfood.py
  - InstaAddict/core/tui.py
files_affected:
  - InstaAddict/core/views.py
  - InstaAddict/core/decorators.py
  - InstaAddict/core/utils.py
  - InstaAddict/core/session_state.py
  - InstaAddict/core/dogfood.py
  - InstaAddict/core/tui.py
  - test/test_subscreen_escape_and_restart_resilience.py
tokens_est: 3500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: '2026-09-19'
completed: '2026-09-20'
override_reason:
---

# Route-060: Subscreen Auto-Escape, Defensive HomeView Navigation, Telemetry & Dogfooding System

## Context & Objectives
Audit #092 diagnosed that live runs crashed when `TabBarView.navigateToSearch()` was invoked while the screen was on a Search Results subscreen (`jackrussellmoments`). On subscreens, the bottom navigation bar is hidden. When `SEARCH_TAB` was not found, legacy fallback code invoked `HomeView.navigateToSearch()`, which executed an unchecked `search_btn.click()` that crashed with `UiObjectNotFoundError`. When `@run_safely` caught the exception and invoked `restart()`, an unguarded `TabBarView(device).navigateToProfile()` crashed the entire process while `atx-agent` was recovering and Instagram was on its splash screen.

Audit #093 isolated 5 additional gaps:
1. `totalSubscreenEscapes` metric missing from `SessionState` and `SessionStateEncoder.default`.
2. `DogfoodOptimizer` in `dogfood.py` ignoring subscreen escapes, escape failures, and restart failures.
3. `DashboardState` in `tui.py` lacking `subscreen_escapes` operational counter.
4. `TabBarView._navigateTo()` retry block omitting `ORDERS` and `ACTIVITY` tab re-resolution.
5. Timing shortcuts (raw `sleep(1)` instead of organic `random_sleep` jitter).

## Key Changes
1. **Subscreen Auto-Escape & Telemetry in `TabBarView` (`InstaAddict/core/views.py`)**:
   - Back out of subscreens up to 3 times (with dialog sweeps) using randomized jitter `random_sleep(0.8, 1.4)`.
   - On verified recovery, increment `SessionState.get_active().increment_subscreen_escapes()`.
   - Add `ORDERS` and `ACTIVITY` to `_navigateTo` retry re-resolution block for 100% enum symmetry.
2. **Defensive Guard in `HomeView.navigateToSearch` (`InstaAddict/core/views.py`)**:
   - Guard `search_btn.click()` with `if not search_btn.exists(Timeout.SHORT): return None`.
3. **Resilient Recovery in `restart()` (`InstaAddict/core/decorators.py`)**:
   - Wrap `TabBarView(device).navigateToProfile()` in `restart()` with a settle check and `try...except` retry block to absorb transient RPC restarts and splash delays.
4. **UI Readiness Check in `open_instagram` (`InstaAddict/core/utils.py`)**:
   - Settle wait (up to 8s) for main UI components with `random_sleep(0.8, 1.4)` between checks.
5. **Observability & TUI Integration (`InstaAddict/core/session_state.py` & `InstaAddict/core/tui.py`)**:
   - Add `totalSubscreenEscapes` and `increment_subscreen_escapes()` to `SessionState`.
   - Serialize `total_subscreen_escapes` in `SessionStateEncoder`.
   - Track and render `subscreen_escapes` in `DashboardState` and `DashboardManager`.
6. **Dogfooding Diagnostics & Recommendations (`InstaAddict/core/dogfood.py`)**:
   - Parse subscreen escapes, escape failures, and restart profile failures from error traces.
   - Generate actionable tuning suggestions for `tuning_suggestions.md` and `.json`.
7. **Automated Verification**:
   - Expand `test/test_subscreen_escape_and_restart_resilience.py` to cover all new telemetry and dogfooding paths.
   - Run full regression suite (303+ tests green).
   - Enforce 0 flake8 lint violations.

## Acceptance Criteria
- [x] `TabBarView._navigateTo` automatically escapes subscreens and increments `SessionState.totalSubscreenEscapes`.
- [x] `ORDERS` and `ACTIVITY` tabs are re-resolved symmetrically on retry.
- [x] `HomeView.navigateToSearch` never crashes with `UiObjectNotFoundError` on missing search buttons.
- [x] `restart()` handles transient RPC errors and splash delays during `navigateToProfile()` gracefully without process termination.
- [x] `open_instagram()` verifies main UI readiness before returning using organic jitter.
- [x] `SessionState` and `SessionStateEncoder` serialize `total_subscreen_escapes`.
- [x] `DogfoodOptimizer` identifies subscreen escape failures and restart failures, outputting actionable tuning suggestions.
- [x] `DashboardState` synchronizes and displays `subscreen_escapes`.
- [x] Unit test suite created and passing 100%.
- [x] Full regression suite passing with zero failures.
- [x] Zero flake8 linting violations.

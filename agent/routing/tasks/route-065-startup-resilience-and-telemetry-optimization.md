---
id: route-065
title: Startup Resilience, Fast ADB Metadata Fallback, PyPI 404 Toleration & Self-Learning Telemetry Expansion
task_type: bugfix
milestone: M7
complexity: medium
executor: Antigravity
context_required:
  - InstaAddict/core/device_facade.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/utils.py
  - InstaAddict/core/dogfood.py
  - InstaAddict/core/telemetry.py
  - test/test_tuning_and_operational_fixes.py
files_affected:
  - InstaAddict/core/device_facade.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/utils.py
  - InstaAddict/core/dogfood.py
  - InstaAddict/core/telemetry.py
  - test/test_tuning_and_operational_fixes.py
tokens_est: 2800
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-25
completed: '2026-09-25'
override_reason:
---

# Route-065: Startup Resilience, Fast ADB Metadata Fallback, PyPI 404 Toleration & Self-Learning Telemetry Expansion

## Objectives
1. **CO-076**: Fast ADB Metadata Fallback in `DeviceFacade`:
   - Implement `_get_info_via_adb()` using direct `adb shell` calls (`getprop ro.product.model`, `getprop ro.build.version.sdk`, `wm size`, `wm density`, `dumpsys power`).
   - In `DeviceFacade.get_info()`, reduce RPC retries from 5 to 2 with a fast timeout (3s) and fall back immediately to `_get_info_via_adb()` on failure, eliminating the 45-minute fatal startup hang.
   - In `get_device_info(device)`, call `device.get_info()` **once**, cache the result dictionary, and extract fields safely using `.get()` with sensible defaults.
2. **CO-077**: PyPI Update Check Graceful Handling:
   - In `utils.py:update_available()`, detect HTTP 404 responses for unindexed package releases (e.g. source/git installs of `InstaAddict-AI`) and log at `DEBUG` rather than `ERROR`.
   - In `check_if_updated()`, eliminate alarming `logger.error("Unable to get latest version from pypi!")` during development runs.
3. **CO-078**: Expand `DogfoodOptimizer` & `PerformanceTracker` Telemetry:
   - In `DogfoodOptimizer._analyze_error_log()`, parse:
     - `rpc_disconnects`: UiAutomation disconnects and GatewayErrors.
     - `adb_timeouts`: ADB shell command timeouts from Watchdog.
     - `watchdog_tier1_triggers`: Watchdog Tier 1 soft recovery events.
     - `watchdog_tier2_triggers`: Watchdog Tier 2 task skip events.
     - `watchdog_tier3_triggers`: Watchdog Tier 3 app restart events.
     - `grid_traps`: Zero-displacement hashtag grid traps.
   - In `DogfoodOptimizer.analyze()` recommendations, emit actionable advice for RPC/ADB latency and Watchdog triggers.
   - In `PerformanceTracker`, track RPC error counts, latency tail percentiles, and device health metrics.
4. **CO-079**: In `DeviceFacade`:
   - Add `is_screen_on()` helper with direct ADB power status fallback.
   - Replace redundant `device.get_info()["screenOn"]` in `bot_flow.py` with `device.is_screen_on()`.
5. Add comprehensive unit tests in `test/test_tuning_and_operational_fixes.py` verifying all fallbacks, error parsing, and telemetry paths.

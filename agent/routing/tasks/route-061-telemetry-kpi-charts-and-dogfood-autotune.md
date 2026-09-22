---
id: route-061
title: Implement Performance Latency Profiling, Motion Sentinel, Micro-Stall Detection, Autonomous Dogfooding Auto-Tune, and [CTRL+G] Terminal KPI Charts Interface
task_type: feature-integration
milestone: null
complexity: high
executor: Antigravity
context_required:
  - agent/reports/audit-096-telemetry-performance-and-self-improvement.md
  - agent/reports/audit-097-pre-impl-telemetry-kpi-charts-and-autotune.md
  - InstaAddict/core/tui.py
  - InstaAddict/core/session_state.py
  - InstaAddict/core/dogfood.py
  - InstaAddict/core/device_facade.py
  - InstaAddict/core/views.py
  - InstaAddict/plugins/core_arguments.py
files_affected:
  - InstaAddict/core/telemetry.py
  - InstaAddict/core/session_state.py
  - InstaAddict/core/dogfood.py
  - InstaAddict/core/device_facade.py
  - InstaAddict/core/views.py
  - InstaAddict/core/tui.py
  - InstaAddict/plugins/core_arguments.py
  - InstaAddict/plugins/interact_reels.py
  - InstaAddict/core/handle_sources.py
  - test/test_telemetry_and_kpi_charts.py
tokens_est: 8000
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: '2026-09-20'
completed: '2026-09-20'
override_reason:
---

# Route-061: Performance Profiling, Motion Sentinel, Micro-Stall Detection, Dogfood Auto-Tune, and [CTRL+G] Terminal KPI Charts Interface

## Context & Objectives
Audit #096 identified that while InstaAddict has robust operational counter metrics, out-of-band deadlock recovery (BotWatchdog), and passive advisory analysis (DogfoodOptimizer), critical blindspots exist in:
1. **Zero Latency Profiling**: No timing measurements for UI view transitions (Profile load, Search load, Post open), UIAutomator RPC latency, or Vision AI roundtrips.
2. **Blind Scrolling Physics**: Swipes are issued blindly with zero verification of physical viewport displacement ($\Delta y$), leading to undetected snapbacks and sticky scrolls.
3. **High Timeout Latency Threshold**: Stalls are only caught when an element lookup exhausts its timeout (3-8s) or when BotWatchdog fires at 90s.
4. **Passive Advisory Dogfooding**: DogfoodOptimizer outputs markdown recommendations, but lacks an online or automated CLI closed-loop mechanism (`--auto-tune`) to adapt parameters safely.
5. **Interactive Operational Visibility**: Operators need a dedicated second terminal interface accessible via `[CTRL+G]` that renders high-fidelity Rich Unicode charts visualizing conversion funnels, quota velocity histograms, latency percentiles, and motion stability health.

## Core Architectural Deliverables

### 1. High-Resolution Performance Telemetry Engine (`InstaAddict/core/telemetry.py`)
- Implement `PerformanceTracker` singleton with zero-overhead nanosecond/millisecond timing via `time.perf_counter()`.
- Context manager `with tracker.measure(category, operation): ...`.
- Capture sample count, error count, min, max, average, P50 (median), and P95 latency percentiles.
- Bound in-memory duration deques (max 200 samples) to prevent memory growth during multi-day sessions.
- Instrument critical execution paths:
  - `view.profile_load` (in `ProfileView.getProfileInfo`)
  - `view.post_open` (in `PostsGridView.navigateToPost`)
  - `view.search_query` (in `SearchView.navigate_to_target`)
  - `api.gemini_vision` (in `GeminiVisionCommenter.evaluate_and_comment_reel`)
  - `rpc.hierarchy_dump` (in `DeviceFacade.dump_hierarchy` or `get_info`)

### 2. Viewport Motion Sentinel & Dynamic Displacement Tracking
- Track motion metrics in `DeviceFacade.swipe_points` and `DeviceFacade.swipe`:
  - `total_swipes`, `displaced_swipes`, `zero_displacement_swipes`, `snapback_events`.
  - Calculate displacement efficiency %: `(displaced_swipes / total_swipes) * 100`.
- Adaptive swipe distance scaling:
  - When consecutive zero-displacement is detected, dynamically boost scale by 20% (up to 0.85).
  - Automatically decay back to default baseline once displacement succeeds.

### 3. Micro-Stall & Early Hang Sentinel
- Implement `MicroStallSentinel` in `UniversalActions`:
  - Detect micro-stalls within 15-20s (e.g. 3 consecutive element lookup timeouts).
  - Execute proactive soft recovery: `UniversalActions.dismiss_dialog(device)` and `device.back()`.
  - Increment `SessionState.totalMicroStallEscapes` and log warning before BotWatchdog reaches 90s.

### 4. Autonomous Closed-Loop Dogfooding & Auto-Tuning (`--auto-tune`)
- Extend `DogfoodOptimizer` (`InstaAddict/core/dogfood.py`):
  - Ingest latency percentiles (P95 ms), zero-displacement rates, and 429 quota events.
  - Implement `apply_tuning(dry_run=False, backup=True)`:
    - Create timestamped backup `accounts/{username}/config.yml.bak`.
    - Adjust `delay-mean` conservatively based on observed P95 latency (bounded 1.0s - 15.0s).
    - Adjust `evaluate-percentage` if 429 quota events occurred (bounded 20% - 100%).
    - Adjust `interact-percentage` if filter pass rates are high.
  - Register `--auto-tune` CLI flag in `InstaAddict/plugins/core_arguments.py`.

### 5. Second Terminal Interface via [CTRL+G] with Stunning KPI Charts (`InstaAddict/core/tui.py`)
- Cross-platform non-blocking keyboard listener support for `[CTRL+G]`:
  - Windows `msvcrt`: `b"\x07"` (byte 7 / BEL)
  - Unix `sys.stdin`: `"\x07"`
  - Character fallbacks: `'g'`, `'G'`
- Toggle view mode in `DashboardManager`:
  - `ViewMode.LIVE_DASHBOARD` (default live dashboard with rolling console)
  - `ViewMode.STATISTICS_CHARTS` (second terminal interface with Rich terminal charts)
- Render 4 state-of-the-art terminal KPI charts:
  1. **Engagement & Conversion Funnel**:
     - Horizontal gradient bars using sub-block unicode glyphs (`█`, `▉`, `▊`, `▋`, `▌`, `▍`, `▎`, `▏`).
     - Visual stages: Scanned -> Profiles Checked -> Filter Passed -> Interacted -> Liked / Followed / Commented.
     - Step conversion rates (% drop-off per funnel stage).
  2. **Quota & Hourly Throughput Velocity**:
     - Visual pace gauges comparing current counts, session limits, and hourly run rates (actions/hour).
  3. **Latency Profile Percentile Distribution**:
     - P50 (median) & P95 (tail) comparison bars for Profile Load, Post Open, Search, and Vision AI.
     - Color-coded latency thresholds (Green < 1200ms, Yellow 1200-2500ms, Red > 2500ms).
  4. **Motion Dynamics & System Health Matrix**:
     - Displacement efficiency %, snapback counts, micro-stall escapes, watchdog recoveries, adaptive settle multiplier.
- Dynamic footer indicator showing `[Ctrl+G] KPI Charts` or `[Ctrl+G] Live Dashboard`.

### 6. Persistence & Serialization Integration
- Add `durationsP50`, `durationsP95`, `totalSwipes`, `zeroDisplacementSwipes`, `snapbackEvents`, and `totalMicroStallEscapes` to `SessionState`.
- Serialize in `SessionStateEncoder.default` to preserve across runs in `sessions.json`.

### 7. Comprehensive Unit Testing & Regression Verification
- Build comprehensive test suite `test/test_telemetry_and_kpi_charts.py` covering:
  - `PerformanceTracker` measurement, P50/P95 percentile calculation, and bounded deque eviction.
  - `KeyboardListenerThread` `[CTRL+G]` (`b"\x07"`) chord decoding and view mode toggle.
  - Terminal charts rendering without exceptions, ANSI leakage, or dimension overflows.
  - `DogfoodOptimizer.apply_tuning()` with backup creation and YAML parameter validation.
  - Full repository regression suite verification (100% green).

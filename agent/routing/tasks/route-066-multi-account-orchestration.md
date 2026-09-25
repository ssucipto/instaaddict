---
id: route-066
title: Multi-Account Management, Process Orchestration & Unified Dashboard Architecture
task_type: feature
milestone: M11
complexity: high
executor: Antigravity
context_required:
  - agent/design/multi-account-orchestration-design.md
  - agent/milestones/milestone-11-multi-account-orchestration.md
  - agent/tasks/milestone-11-multi-account-orchestration/task-42-multi-account-config.md
  - agent/tasks/milestone-11-multi-account-orchestration/task-43-account-orchestrator.md
  - agent/tasks/milestone-11-multi-account-orchestration/task-44-status-beacon-ipc.md
  - agent/tasks/milestone-11-multi-account-orchestration/task-45-multi-account-dashboard.md
  - agent/tasks/milestone-11-multi-account-orchestration/task-46-cli-multi-command.md
  - agent/tasks/milestone-11-multi-account-orchestration/task-47-health-monitor-auto-recovery.md
  - agent/tasks/milestone-11-multi-account-orchestration/task-48-multi-account-telemetry.md
  - agent/tasks/milestone-11-multi-account-orchestration/task-49-telegram-multi-account.md
files_affected:
  - InstaAddict/core/multi_config.py
  - InstaAddict/core/orchestrator.py
  - InstaAddict/core/beacon.py
  - InstaAddict/core/multi_dashboard.py
  - InstaAddict/core/health_monitor.py
  - InstaAddict/core/multi_telemetry.py
  - InstaAddict/core/bot_flow.py
  - InstaAddict/core/core_arguments.py
  - InstaAddict/__main__.py
  - InstaAddict/core/telegram.py
  - config-examples/multi_config.yml
  - test/test_multi_account_orchestration.py
tokens_est: 4500
tokens_actual:
cost_est_usd:
cost_actual_usd:
created: 2026-09-25
completed: 2026-09-25
override_reason:
---

# Route-066: Multi-Account Management, Process Orchestration & Unified Dashboard Architecture

## Objectives

1. **Architecture & Foundation (Tasks 42, 43, 44)**:
   - Implement `MultiAccountConfig` parser with YAML schema validation, unique device/account enforcement, actionable `MultiConfigValidationError` diagnostics (GAP-20), per-account `gemini_api_key` quota segregation (GAP-09), `global_blacklist`/`whitelist` (GAP-13), and priority sorting.
   - Build `AccountOrchestrator` process supervisor managing N isolated child bot subprocesses via `subprocess.Popen` with staggered starts, pre-flight `adb devices` check (GAP-05), `sys.boot_completed == "1"` and `init.svc.bootanim == "stopped"` boot validation (GAP-16), exclusive PID file locking `orchestrator.pid` with orphan reaping (GAP-11), direct log redirection with bounded 10MB rotation to `logs/orchestrator/{username}_stdout.log` (GAP-02, GAP-15), and explicit `--device` CLI overrides (GAP-04).
   - Enforce `INSTAADDICT_MULTI_ACCOUNT=1` environment flag to prevent child processes from executing global `adb kill-server` (GAP-08).
   - Implement dual-phase graceful shutdown with `accounts/<username>/.stop` sentinel before fallback to SIGTERM/terminate (GAP-03).
   - Build `StatusBeaconWriter` daemon thread writing `.status.json` atomic beacons and `BeaconReader` for file-based IPC with 3-attempt retry tolerance for Windows file-lock contention (GAP-06).

2. **Management Interface & CLI (Tasks 45, 46)**:
   - Implement `MultiAccountDashboard` Rich Live interface with live multi-card and summary table views, status badges, live KPI bars, and non-blocking command shortcuts.
   - Throttle TUI rendering with 1.0 FPS render governor and mtime dirty-checking to keep CPU usage <0.5% (GAP-19).
   - Support zero-downtime configuration hot-reloading via `[C]` key in dashboard and `python run.py multi --reload` in CLI (GAP-21).
   - Harden Windows terminal listener with strict `CONIN$` console mode restoration in `try...finally` and `atexit` (GAP-14).
   - Add `multi` subcommand in `core_arguments.py` and `__main__.py` with `--config`, `--only`, `--status`, `--stop`, `--restart`, `--reload`, and `--no-tui` options. Maintain 100% backwards compatibility for `run.py --config ...` (GAP-07).

3. **Autonomous Resilience & Intelligence (Tasks 47, 48, 49)**:
   - Implement `HealthMonitor` detecting stale heartbeats (>45s), process crashes, and offline ADB emulators with auto-recovery and rate-limited restart backoff.
   - Prevent thundering herd restart storms via serialized auto-recovery queue with 15s gap and randomized exponential backoff jitter (GAP-18).
   - Distinguish intentional safety limit exits (`status: "limit_reached"`) from fatal crashes to prevent infinite restart loops (GAP-12).
   - Implement `MultiAccountTelemetryAggregator` synthesizing `sessions.json`, `DogfoodOptimizer` recommendations, and latency metrics across accounts into fleet reports.
   - Trigger dynamic account reboot when Dogfood auto-tuning is applied so calibrated parameters reload immediately (GAP-10).
   - Extend Telegram bot with centralized `getUpdates` inbox polling in the orchestrator (`INSTAADDICT_NO_TELEGRAM_INBOX=1` in child processes to prevent HTTP 409 collisions) (GAP-01), multi-account target commands (`/status @account`, `/restart @account`, `/post @account`), and fleet event alerts.

4. **Zero Regressions & Rigorous Headless CI Testing (GAP-17)**:
   - Maintain complete backwards compatibility for existing single-account operations.
   - Build comprehensive headless mock harness in `test/test_multi_account_orchestration.py` (`MockSubprocessPopen`, `MockAdbDevices`, `MockStatusBeacon`, `MockConsole`) guaranteeing fast, reliable execution in CI (GAP-17).
   - Ensure all 420+ existing repository tests remain 100% green.

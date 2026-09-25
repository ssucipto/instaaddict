# Design: Multi-Account Orchestration Architecture

**Created**: 2026-09-25
**Status**: Draft
**Milestone**: M11 (Multi-Account Management & Orchestration)
**Author**: ACP Agent

---

## 1. Problem Statement

InstaAddict-AI currently supports **one Instagram account per process invocation**. The bot is launched with `--config accounts/<username>/config.yml`, binds to a single Android emulator device (`device: emulator-5554`), and runs a single-threaded session loop. All core subsystems — `DashboardManager`, `BotWatchdog`, `PerformanceTracker`, `SessionState._active_session` — are **process-wide singletons** with no concept of account isolation.

To manage N Instagram accounts running simultaneously on N assigned Android emulators, we need an orchestration layer that:

1. Spawns and supervises N independent bot processes
2. Provides a unified management dashboard aggregating all accounts
3. Leverages existing telemetry, dogfood, and logging infrastructure per-account
4. Does not regress existing single-account functionality

---

## 2. Architecture Decision: Multi-Process (Not Multi-Thread)

### Decision: **Spawn N separate OS processes** — one per account

### Rationale

| Approach | Pros | Cons |
|----------|------|------|
| **Multi-Thread** (single process) | Shared memory, lower overhead | Requires rewriting ALL singletons (`DashboardManager`, `BotWatchdog`, `PerformanceTracker`, `SessionState`) to be instance-scoped. `uiautomator2.Device` objects share process globals. Python GIL limits true parallelism. **HIGH REGRESSION RISK**. |
| **Multi-Process** (N subprocesses) | ✅ Zero changes to existing bot code. ✅ Each process has its own singletons, device connection, and state. ✅ Crash isolation (one account crash doesn't kill others). ✅ Natural per-process logging. ✅ Cross-platform (Windows/Linux). | Higher memory (~50-80MB per process). Requires IPC for aggregated dashboard. |
| **Container-Based** (Docker) | Strong isolation | Requires Docker + ADB passthrough. Overkill for local use. |

**Winner: Multi-Process** — minimal regression risk, natural isolation, and leverages all existing infrastructure unchanged.

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                       │
│          InstaAddict/core/orchestrator.py            │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ ProcessMgr  │  │ HealthMonitor│  │  IPC Server  │ │
│  │ spawn/kill  │  │ heartbeats   │  │  status agg  │ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                │                  │         │
│  ┌──────┴──────────────┬─┴──────────────────┘         │
│  │                     │                              │
│  ▼                     ▼                              │
│ subprocess.Popen  subprocess.Popen  ...               │
│ [Bot: acct_1]     [Bot: acct_2]                       │
│  device: emu-5554  device: emu-5556                   │
│  PID: 12345        PID: 12346                         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              MANAGEMENT DASHBOARD                    │
│        InstaAddict/core/multi_dashboard.py           │
│                                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Unified TUI (Rich Live)                        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │ │
│  │  │ Account 1│ │ Account 2│ │ Account N│        │ │
│  │  │ Status   │ │ Status   │ │ Status   │        │ │
│  │  │ Metrics  │ │ Metrics  │ │ Metrics  │        │ │
│  │  └──────────┘ └──────────┘ └──────────┘        │ │
│  │                                                 │ │
│  │  [R] Restart  [S] Stop  [P] Pause  [A] Add     │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Multi-Account Configuration (`multi_config.yml`)

New top-level config file at project root:

```yaml
# multi_config.yml — Multi-Account Orchestration Configuration
orchestrator:
  max_concurrent: 5
  stagger_start_seconds: 30-60     # Randomized stagger between account starts
  health_check_interval: 15        # Seconds between health polls
  auto_restart: true               # Restart crashed accounts
  max_restart_attempts: 3          # Per account per hour
  log_dir: logs/orchestrator       # Orchestrator-level logs

accounts:
  - username: lolatheozjack
    config: accounts/lolatheozjack/config.yml
    device: emulator-5554
    enabled: true
    priority: 1                    # Higher priority = started first
    schedule:                      # Optional per-account override
      working_hours: "06:00-23:59"

  - username: another_account
    config: accounts/another_account/config.yml
    device: emulator-5556
    enabled: true
    priority: 2

  - username: third_account
    config: accounts/third_account/config.yml
    device: emulator-5558
    enabled: false                 # Disabled — skip
    priority: 3
```

**Key design decisions:**
- Each account **MUST** have a unique `device` assignment (1:1 account-to-emulator mapping)
- Stagger start prevents ADB port conflicts and reduces detection risk
- Per-account configs remain in `accounts/<username>/config.yml` (existing format, zero migration)
- `multi_config.yml` is purely additive — single-account mode (`run.py --config ...`) continues to work unchanged

### 4.2 Orchestrator (`InstaAddict/core/orchestrator.py`)

#### Class: `AccountOrchestrator`

```python
class AccountOrchestrator:
    """Spawns, monitors, and manages multiple InstaAddict bot processes."""

    def __init__(self, config_path: str = "multi_config.yml"):
        self.config = self._load_config(config_path)
        self.processes: Dict[str, AccountProcess] = {}
        self.health_monitor: HealthMonitor = HealthMonitor(...)
        self.ipc_server: IPCServer = IPCServer(...)

    def start_all(self):
        """Spawn bot processes for all enabled accounts with staggered starts."""

    def stop_all(self):
        """Gracefully stop all running bots."""

    def restart_account(self, username: str):
        """Restart a specific account's bot process."""

    def get_aggregate_status(self) -> Dict:
        """Collect status from all running accounts via IPC."""
```

#### Class: `AccountProcess`

```python
@dataclass
class AccountProcess:
    username: str
    config_path: str
    device_id: str
    process: Optional[subprocess.Popen]
    pid: Optional[int]
    status: str  # "starting" | "running" | "sleeping" | "crashed" | "stopped"
    started_at: Optional[datetime]
    restart_count: int
    last_heartbeat: Optional[datetime]
    last_error: Optional[str]
```

#### Process Spawning

Each bot is spawned as:
```python
subprocess.Popen(
    [sys.executable, "run.py", "--config", account.config_path],
    cwd=project_root,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env={**os.environ, "INSTAADDICT_ACCOUNT": username, "INSTAADDICT_NO_TUI": "1"},
)
```

**Critical**: Child processes run with `INSTAADDICT_NO_TUI=1` to disable per-process TUI (the orchestrator runs its own unified dashboard).

### 4.3 Inter-Process Communication (IPC)

#### Mechanism: **File-Based Status Beacons** (cross-platform, zero-dependency)

Each bot process writes a JSON status beacon file every 10 seconds:

```
accounts/<username>/.status.json
```

```json
{
  "pid": 12345,
  "status": "running",
  "session_index": 3,
  "uptime_seconds": 3600,
  "heartbeat": "2026-09-25T10:30:00",
  "current_job": "hashtag-posts-recent: #jackrussell",
  "metrics": {
    "total_likes": 15,
    "total_follows": 4,
    "total_comments": 2,
    "total_watched": 12,
    "total_crashes": 0,
    "total_unfollowed": 5,
    "session_started": "2026-09-25T10:00:00"
  },
  "device": {
    "id": "emulator-5554",
    "screen_on": true,
    "sdk_int": 35
  },
  "errors": []
}
```

**Why file-based over sockets/pipes:**
- Cross-platform (Windows + Linux) without dependencies
- Naturally crash-safe (stale file = crashed process)
- Can be read by orchestrator, dashboard, Telegram bot, or external monitoring
- Atomic writes via `atomicwrites` (already a dependency)

### 4.4 Health Monitor (`HealthMonitor`)

Runs in the orchestrator process's background thread:

```python
class HealthMonitor(threading.Thread):
    """Periodically reads status beacons and detects unhealthy accounts."""

    STALE_THRESHOLD = 45  # seconds — beacon older than this = unresponsive

    def check_health(self, account: AccountProcess) -> str:
        beacon_path = f"accounts/{account.username}/.status.json"
        if not os.path.exists(beacon_path):
            return "no_beacon"
        beacon = json.load(open(beacon_path))
        age = (datetime.now() - parse(beacon["heartbeat"])).total_seconds()
        if age > self.STALE_THRESHOLD:
            return "stale"
        if beacon.get("status") == "crashed":
            return "crashed"
        return "healthy"
```

**Auto-recovery actions:**
| Health State | Action |
|-------------|--------|
| `healthy` | No action |
| `stale` (>45s no heartbeat) | Log warning, wait one more cycle |
| `stale` (>90s) | Kill process, auto-restart if enabled |
| `crashed` | Auto-restart if attempts < max |
| `no_beacon` (process running but no file) | Wait 60s, then kill+restart |

### 4.5 Management Dashboard (`InstaAddict/core/multi_dashboard.py`)

A new Rich Live TUI that replaces the per-account dashboard when running in multi-account mode:

```
╔══════════════════════════════════════════════════════════════════╗
║  InstaAddict-AI  Multi-Account Manager  v1.5.0                  ║
║  Accounts: 3/3 active  │  Uptime: 4h 23m  │  ♥ All Healthy     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─ @lolatheozjack ────────────────────────────────────────────┐ ║
║  │ Status: RUNNING  │  Device: emulator-5554  │  Session: #5   │ ║
║  │ Job: hashtag-posts-recent: #jackrussell                     │ ║
║  │ Likes: 15/25  Follows: 4/15  Comments: 2/7  Watched: 12/30 │ ║
║  │ Crashes: 0  │  Uptime: 2h 15m  │  ♥ Healthy                │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                  ║
║  ┌─ @another_account ──────────────────────────────────────────┐ ║
║  │ Status: SLEEPING │  Device: emulator-5556  │  Session: #3   │ ║
║  │ Next wake: 14:30 (in 45m)                                   │ ║
║  │ Likes: 22/25  Follows: 8/10  Comments: 5/7  Watched: 28/30 │ ║
║  │ Crashes: 1  │  Uptime: 4h 23m  │  ⚠ 1 crash               │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                  ║
║  ┌─ @third_account ────────────────────────────────────────────┐ ║
║  │ Status: DISABLED │  Not running                             │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  [R] Restart  [S] Stop  [P] Pause  [E] Enable/Disable          ║
║  [L] View Logs  [T] Tuning Report  [D] Dogfood  [Q] Quit All   ║
╚══════════════════════════════════════════════════════════════════╝
```

### 4.6 CLI Interface

New subcommand in `__main__.py`:

```
python run.py multi                           # Start all accounts from multi_config.yml
python run.py multi --config multi_config.yml # Explicit config path
python run.py multi --only lolatheozjack      # Start single account in multi-mode
python run.py multi --status                  # Show status of running accounts
python run.py multi --stop                    # Stop all running accounts
python run.py multi --stop lolatheozjack      # Stop specific account
python run.py multi --restart another_account # Restart specific account
```

**Backwards compatibility**: `python run.py --config accounts/lolatheozjack/config.yml` continues to work exactly as before (single-account mode).

### 4.7 Beacon Writer (In Bot Process)

Minimal addition to `bot_flow.py` — a background thread writing `.status.json`:

```python
class StatusBeaconWriter(threading.Thread):
    """Writes periodic status beacons for orchestrator consumption."""

    def __init__(self, username: str, interval: float = 10.0):
        super().__init__(daemon=True, name=f"beacon-{username}")
        self.username = username
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            self._write_beacon()
            self._stop_event.wait(self.interval)

    def _write_beacon(self):
        session = SessionState.get_active()
        # ... serialize to accounts/<username>/.status.json
```

### 4.8 Aggregated Telemetry & Dogfood

The orchestrator aggregates per-account telemetry:

```python
class MultiAccountTelemetry:
    """Aggregates telemetry across all managed accounts."""

    def aggregate_report(self) -> Dict:
        """Read all accounts' sessions.json and tuning_suggestions.json."""
        report = {}
        for account in self.accounts:
            optimizer = DogfoodOptimizer(account.username)
            report[account.username] = optimizer.analyze()
        return report

    def cross_account_insights(self) -> List[str]:
        """Compare performance across accounts for optimization."""
        # e.g., "Account A has 3x higher crash rate than B — check device stability"
```

### 4.9 Telegram Integration

Extend existing Telegram bot to support multi-account commands:

```
/status              → Show all accounts
/status @lolatheozjack → Show specific account
/stop @lolatheozjack   → Stop specific account
/restart @lolatheozjack → Restart specific account
/post @lolatheozjack   → Queue post for specific account
```

---

## 5. Per-Account Data Isolation

All per-account data stays in existing paths (no migration needed):

| Data | Path | Isolation |
|------|------|-----------|
| Config | `accounts/<username>/config.yml` | ✅ Already isolated |
| Filters | `accounts/<username>/filters.yml` | ✅ Already isolated |
| Sessions | `accounts/<username>/sessions.json` | ✅ Already isolated |
| Interacted Users | `accounts/<username>/interacted_users.json` | ✅ Already isolated |
| History | `accounts/<username>/history.md` | ✅ Already isolated |
| Tuning | `accounts/<username>/tuning_suggestions.json` | ✅ Already isolated |
| Content Queue | `accounts/<username>/content_queue/` | ✅ Already isolated |
| Logs | `logs/<username>.log` | ✅ Already isolated |
| Error Trace | `logs/<username>_error_trace.log` | ✅ Already isolated |
| Reports | `accounts/<username>/reports/` | ✅ Already isolated |
| **NEW** Status Beacon | `accounts/<username>/.status.json` | ✅ Naturally isolated |

**The existing per-account directory structure is already perfectly isolated.** This is why multi-process is the ideal approach.

---

## 6. Regression Prevention

### What Changes

| Component | Change | Risk |
|-----------|--------|------|
| `bot_flow.py` | Add `StatusBeaconWriter` thread start | LOW — additive, daemon thread |
| `__main__.py` | Add `multi` subcommand | LOW — additive, no existing flow touched |
| **NEW** `orchestrator.py` | New file | ZERO — new code |
| **NEW** `multi_dashboard.py` | New file | ZERO — new code |
| **NEW** `multi_config.yml` | New file | ZERO — new file |

### What Doesn't Change

- `Config`, `DeviceFacade`, `SessionState`, `DashboardManager`, `BotWatchdog`, `PerformanceTracker` — **zero changes**
- All singleton patterns remain process-scoped (naturally isolated by multi-process)
- `run.py --config ...` single-account mode — **completely unchanged**
- All 420+ unit tests — **unaffected**

---

## 7. Implementation Phases

### Phase 1: Foundation (Tasks 42-44)
- Create `multi_config.yml` schema and parser
- Build `AccountOrchestrator` with process spawn/kill lifecycle
- Add `StatusBeaconWriter` to `bot_flow.py`

### Phase 2: Management Interface (Tasks 45-46)
- Build `multi_dashboard.py` unified Rich TUI
- Add `multi` subcommand to `__main__.py` CLI

### Phase 3: Intelligence & Resilience (Tasks 47-48)
- Implement `HealthMonitor` with auto-restart
- Build `MultiAccountTelemetry` aggregated dogfood
- Extend Telegram bot for multi-account commands

---

## 8. Future Extensions (Not In Scope)

- Web-based management dashboard (Flask/FastAPI)
- Automatic emulator provisioning (creating AVDs on demand)
- Account rotation (cycling accounts on same device)
- Cloud deployment (Docker Compose / Kubernetes)
- Remote management API (REST/gRPC)

---

## 9. Key Technical Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Multi-process over multi-thread | Zero singleton refactoring, crash isolation, GIL avoidance |
| D2 | File-based IPC over sockets | Cross-platform, crash-safe, zero-dependency, human-readable |
| D3 | 1:1 account-to-device mapping | ADB requirement, anti-detection best practice |
| D4 | Orchestrator runs its own TUI | Child processes run headless (`INSTAADDICT_NO_TUI=1`) |
| D5 | Staggered starts | Reduce ADB contention and detection fingerprint |
| D6 | Additive-only changes to existing code | Regression prevention — new files, not refactored singletons |
| D7 | Centralized Telegram inbox polling | Prevent concurrent getUpdates HTTP 409 collisions (GAP-01) |
| D8 | Direct log file redirection | Prevent 64KB OS pipe buffer deadlocks on verbose subprocesses (GAP-02) |
| D9 | Dual-phase graceful shutdown | File-based `.stop` flag allows clean shutdown before SIGTERM/kill (GAP-03) |
| D10 | Explicit CLI `--device` override | Guarantee `multi_config.yml` takes absolute precedence over YAML (GAP-04) |
| D11 | Device-scoped ADB transport recovery | Suppress `adb kill-server` in child processes; protect sibling sessions (GAP-08) |
| D12 | Per-account Gemini API keys | Quota segregation across accounts to prevent 429 exhaustion (GAP-09) |
| D13 | Auto-tune dynamic process reboot | Gracefully cycle account process when Dogfood modifies config (GAP-10) |
| D14 | Exclusive orchestrator PID lock | Prevent duplicate concurrent orchestrators and reap orphan files (GAP-11) |
| D15 | Subprocess stdout log rotation | 10MB bounded rotation prevents unbounded disk growth (GAP-15) |
| D16 | Emulator boot-completed assertion | Assert sys.boot_completed == 1 before launching automation (GAP-16) |
| D17 | Headless CI test harness | Mock subprocesses and beacons enable fast headless CI verification (GAP-17) |
| D18 | Auto-restart thundering herd prevention | 15s gap with randomized exponential jitter stabilizes recovery (GAP-18) |
| D19 | TUI render governor (<0.5% CPU) | 1 FPS cap with dirty-checking keeps supervisory CPU low (GAP-19) |
| D20 | Defensive configuration validation | MultiConfigValidationError with actionable field diagnostics (GAP-20) |
| D21 | Zero-downtime hot-reloading | [C] key dynamically diffs and updates fleet without stopping active bots (GAP-21) |

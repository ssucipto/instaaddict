import atexit
import json
import logging
import os
import random
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from InstaAddict.core.multi_config import AccountConfig, MultiAccountConfig

logger = logging.getLogger(__name__)


@dataclass
class AccountProcess:
    username: str
    config_path: str
    device_id: str
    enabled: bool = True
    priority: int = 1
    process: Optional[subprocess.Popen] = None
    pid: Optional[int] = None
    status: str = "stopped"  # "starting" | "running" | "sleeping" | "stopped" | "crashed" | "device_offline" | "device_booting" | "limit_reached" | "paused_fault"
    started_at: Optional[datetime] = None
    restart_count: int = 0
    last_restart_time: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    last_error: Optional[str] = None
    stdout_file: Optional[Any] = None


class AccountOrchestrator:
    """
    Central process supervisor that manages N independent InstaAddict bot subprocesses
    (one per Instagram account) across assigned Android emulators with crash isolation,
    exclusive PID locking, bounded log rotation, staggered boots, and zero-downtime hot-reloads.
    """

    PID_FILE_PATH: Optional[str] = None
    MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10MB bounded log rotation (GAP-15)

    def __init__(
        self,
        config: MultiAccountConfig,
        project_root: Optional[str] = None,
        pid_file_path: Optional[str] = None,
    ):
        self.config = config
        self.project_root = project_root or os.getcwd()
        self.log_dir = self.config.orchestrator.log_dir
        os.makedirs(self.log_dir, exist_ok=True)

        if pid_file_path:
            self.pid_file_path = pid_file_path
        elif self.PID_FILE_PATH:
            self.pid_file_path = self.PID_FILE_PATH
        else:
            self.pid_file_path = os.path.join(self.log_dir, "orchestrator.pid")

        self._acquire_pid_lock()

        self.processes: Dict[str, AccountProcess] = {}
        self._init_processes_from_config()

        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Register process-level cleanup
        atexit.register(self._cleanup_on_exit)

    def _acquire_pid_lock(self) -> None:
        """Enforces exclusive PID locking and reaps dead process orphan lock files (GAP-11)."""
        pid_dir = os.path.dirname(self.pid_file_path)
        if pid_dir:
            os.makedirs(pid_dir, exist_ok=True)

        if os.path.exists(self.pid_file_path):
            try:
                with open(self.pid_file_path, "r", encoding="utf-8") as f:
                    old_pid = int(f.read().strip())
                if self._is_pid_running(old_pid):
                    raise RuntimeError(
                        f"Another active AccountOrchestrator is already running (PID: {old_pid}). "
                        f"Terminate it or delete {self.pid_file_path} if stale."
                    )
                else:
                    logger.info(f"Reaping stale orchestrator PID lock for dead PID: {old_pid}")
                    os.remove(self.pid_file_path)
            except (ValueError, OSError):
                if os.path.exists(self.pid_file_path):
                    os.remove(self.pid_file_path)

        current_pid = os.getpid()
        with open(self.pid_file_path, "w", encoding="utf-8") as f:
            f.write(str(current_pid))

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        """Checks if a process with given PID is currently active."""
        if pid <= 0:
            return False
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            except Exception:
                return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

    def _cleanup_on_exit(self) -> None:
        """Removes orchestrator.pid lock file on exit."""
        try:
            target_path = getattr(self, "pid_file_path", None) or self.PID_FILE_PATH
            if target_path and os.path.exists(target_path):
                with open(target_path, "r", encoding="utf-8") as f:
                    p = int(f.read().strip())
                if p == os.getpid():
                    os.remove(target_path)
        except Exception:
            pass

    def _init_processes_from_config(self) -> None:
        """Initializes AccountProcess instances for all configured accounts."""
        for acc in self.config.accounts:
            if acc.username not in self.processes:
                self.processes[acc.username] = AccountProcess(
                    username=acc.username,
                    config_path=acc.config_path,
                    device_id=acc.device_id,
                    enabled=acc.enabled,
                    priority=acc.priority,
                    status="stopped" if acc.enabled else "disabled",
                )

    def _open_stdout_file(self, username: str):
        """Opens stdout/stderr log file with bounded 10MB rotation (GAP-15)."""
        stdout_path = os.path.join(self.log_dir, f"{username}_stdout.log")
        if os.path.exists(stdout_path):
            try:
                if os.path.getsize(stdout_path) > self.MAX_LOG_SIZE_BYTES:
                    backup_path = f"{stdout_path}.1"
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    os.rename(stdout_path, backup_path)
                    logger.info(f"Rotated stdout log for {username} (>10MB) to {backup_path}")
            except Exception as e:
                logger.debug(f"Log rotation check error for {username}: {e}")

        return open(stdout_path, "a", encoding="utf-8")

    def check_device_readiness(self, device_id: str) -> Tuple[bool, str]:
        """
        Validates emulator readiness via adb devices and boot property assertions (GAP-05, GAP-16).
        Returns: (is_ready: bool, reason: str)
        """
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            lines = [
                line.strip()
                for line in res.stdout.splitlines()
                if line.strip() and not line.startswith("List of")
            ]
            matching_lines = [line for line in lines if device_id in line]
            if not matching_lines:
                return False, "DEVICE_NOT_FOUND"

            dev_line = matching_lines[0]
            parts = dev_line.split()
            if len(parts) < 2 or parts[1] != "device":
                return False, "DEVICE_OFFLINE"

            # Check OS boot completion properties (GAP-16)
            boot_res = subprocess.run(
                ["adb", "-s", device_id, "shell", "getprop", "sys.boot_completed"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if boot_res.stdout.strip() != "1":
                return False, "DEVICE_BOOTING"

            anim_res = subprocess.run(
                ["adb", "-s", device_id, "shell", "getprop", "init.svc.bootanim"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if anim_res.stdout.strip() not in ("stopped", ""):
                return False, "DEVICE_BOOTING"

            return True, "READY"
        except Exception as e:
            return False, f"ADB_ERROR: {e}"

    def start_account(self, username: str) -> bool:
        """Spawns an individual account bot subprocess."""
        with self._lock:
            proc_obj = self.processes.get(username)
            if not proc_obj:
                logger.error(f"Cannot start unknown account: {username}")
                return False

            if proc_obj.process and proc_obj.process.poll() is None:
                logger.warning(f"Account {username} is already running (PID: {proc_obj.pid})")
                return True

            acc_cfg = self.config.get_account(username)
            if not acc_cfg or not acc_cfg.enabled:
                logger.info(f"Account {username} is disabled in config.")
                return False

            # Device pre-flight validation (GAP-05, GAP-16)
            is_ready, state = self.check_device_readiness(proc_obj.device_id)
            if not is_ready:
                if state == "DEVICE_BOOTING":
                    logger.warning(f"Device {proc_obj.device_id} for @{username} is booting. Waiting up to 60s...")
                    proc_obj.status = "device_booting"
                    for _ in range(12):
                        time.sleep(5)
                        is_ready, state = self.check_device_readiness(proc_obj.device_id)
                        if is_ready:
                            break
                if not is_ready:
                    logger.error(f"Cannot start @{username}: device {proc_obj.device_id} is not ready ({state})")
                    proc_obj.status = "device_offline" if "OFFLINE" in state or "NOT_FOUND" in state else "device_booting"
                    return False

            # Clean up old .stop sentinel if present
            stop_file = os.path.join("accounts", username, ".stop")
            if os.path.exists(stop_file):
                try:
                    os.remove(stop_file)
                except Exception:
                    pass

            stdout_file = self._open_stdout_file(username)
            proc_obj.stdout_file = stdout_file

            env = {
                **os.environ,
                "INSTAADDICT_ACCOUNT": username,
                "INSTAADDICT_NO_TUI": "1",
                "INSTAADDICT_NO_TELEGRAM_INBOX": "1",  # GAP-01: Prevent concurrent getUpdates collisions
                "INSTAADDICT_MULTI_ACCOUNT": "1",      # GAP-08: Suppress global adb kill-server in children
            }
            if acc_cfg.gemini_api_key:
                env["GEMINI_API_KEY"] = acc_cfg.gemini_api_key  # GAP-09: Quota segregation
            if self.config.orchestrator.global_blacklist:
                env["INSTAADDICT_GLOBAL_BLACKLIST"] = self.config.orchestrator.global_blacklist  # GAP-13
            if self.config.orchestrator.global_whitelist:
                env["INSTAADDICT_GLOBAL_WHITELIST"] = self.config.orchestrator.global_whitelist  # GAP-13

            # Command: explicitly pass --device override (GAP-04)
            cmd = [
                sys.executable,
                "run.py",
                "run",
                "--config",
                proc_obj.config_path,
                "--device",
                proc_obj.device_id,
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=self.project_root,
                    env=env,
                    stdout=stdout_file,
                    stderr=subprocess.STDOUT,  # GAP-02: Direct to file to avoid 64KB OS pipe buffer deadlocks
                )
                proc_obj.process = proc
                proc_obj.pid = proc.pid
                proc_obj.status = "running"
                proc_obj.started_at = datetime.now()
                logger.info(f"Started @{username} on device {proc_obj.device_id} (PID: {proc.pid})")
                return True
            except Exception as e:
                logger.error(f"Failed to spawn bot process for @{username}: {e}")
                proc_obj.status = "crashed"
                proc_obj.last_error = str(e)
                return False

    def stop_account(self, username: str, timeout: float = 10.0) -> bool:
        """
        Executes dual-phase graceful shutdown of a single account bot subprocess (GAP-03).
        Phase 1: Write accounts/<username>/.stop sentinel.
        Phase 2: Wait up to timeout seconds for clean exit.
        Phase 3: Fall back to process.terminate() / process.kill().
        """
        with self._lock:
            proc_obj = self.processes.get(username)
            if not proc_obj or not proc_obj.process:
                return True

            proc = proc_obj.process
            if proc.poll() is not None:
                proc_obj.status = "stopped"
                return True

            logger.info(f"Initiating graceful shutdown for @{username} (PID: {proc_obj.pid})...")

            # Phase 1: Write .stop sentinel (GAP-03)
            acc_dir = os.path.join("accounts", username)
            os.makedirs(acc_dir, exist_ok=True)
            stop_sentinel = os.path.join(acc_dir, ".stop")
            try:
                with open(stop_sentinel, "w", encoding="utf-8") as f:
                    f.write(f"STOP {datetime.now().isoformat()}\n")
            except Exception as e:
                logger.debug(f"Failed to write stop sentinel for @{username}: {e}")

            # Phase 2: Wait up to timeout for self-termination
            start_wait = time.time()
            while time.time() - start_wait < timeout:
                if proc.poll() is not None:
                    logger.info(f"Account @{username} terminated cleanly via .stop sentinel.")
                    break
                time.sleep(0.5)

            # Phase 3: Terminate or kill if still running
            if proc.poll() is None:
                logger.warning(f"Account @{username} did not exit in {timeout}s. Terminating process...")
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

            # Cleanup .stop sentinel
            if os.path.exists(stop_sentinel):
                try:
                    os.remove(stop_sentinel)
                except Exception:
                    pass

            # Close stdout file handle
            if proc_obj.stdout_file:
                try:
                    proc_obj.stdout_file.close()
                except Exception:
                    pass
                proc_obj.stdout_file = None

            proc_obj.status = "stopped"
            return True

    def restart_account(self, username: str, delay_seconds: float = 3.0) -> bool:
        """Stops and restarts an account with delay."""
        logger.info(f"Restarting account @{username}...")
        self.stop_account(username)
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        proc_obj = self.processes.get(username)
        if proc_obj:
            proc_obj.restart_count += 1
            proc_obj.last_restart_time = datetime.now()
        return self.start_account(username)

    def start_all(self) -> None:
        """Starts all enabled accounts in priority order with staggered delays."""
        enabled_accounts = self.config.get_enabled_accounts()
        stagger_range = self.config.orchestrator.stagger_start_seconds

        for idx, acc in enumerate(enabled_accounts):
            self.start_account(acc.username)
            if idx < len(enabled_accounts) - 1:
                # Compute staggered delay
                delay = self._compute_stagger_delay(stagger_range)
                logger.info(f"Staggering next account startup by {delay:.1f}s...")
                time.sleep(delay)

        self._start_monitor_thread()

    def stop_all(self, timeout: float = 10.0) -> None:
        """Stops all running accounts gracefully."""
        logger.info("Stopping all managed bot processes...")
        self._stop_event.set()

        for username in list(self.processes.keys()):
            self.stop_account(username, timeout=timeout)

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)

        self._cleanup_on_exit()

    def reload_config(self) -> Dict[str, str]:
        """
        Dynamically hot-reloads multi_config.yml with zero downtime for undisturbed accounts (GAP-21).
        - Spawns newly added/enabled accounts
        - Stops removed/disabled accounts
        - Leaves unchanged accounts running 100% uninterrupted
        """
        logger.info(f"Reloading multi-account configuration from {self.config.config_path}...")
        try:
            new_config = MultiAccountConfig.load(self.config.config_path or "multi_config.yml")
        except Exception as e:
            logger.error(f"Config reload failed: {e}")
            return {"status": "error", "message": str(e)}

        actions_taken = []
        with self._lock:
            old_usernames = set(self.processes.keys())
            new_accounts_map = {acc.username: acc for acc in new_config.accounts}
            new_usernames = set(new_accounts_map.keys())

            # 1. Accounts removed from config -> stop them
            for removed_user in (old_usernames - new_usernames):
                logger.info(f"Config reload: Account @{removed_user} removed from config. Stopping...")
                self.stop_account(removed_user)
                del self.processes[removed_user]
                actions_taken.append(f"stopped_and_removed:@{removed_user}")

            # 2. Existing accounts: check enabled state changes
            for username, acc_cfg in new_accounts_map.items():
                if username in self.processes:
                    proc_obj = self.processes[username]
                    was_enabled = proc_obj.enabled
                    now_enabled = acc_cfg.enabled

                    proc_obj.enabled = now_enabled
                    proc_obj.priority = acc_cfg.priority
                    proc_obj.device_id = acc_cfg.device_id
                    proc_obj.config_path = acc_cfg.config_path

                    if was_enabled and not now_enabled:
                        logger.info(f"Config reload: Account @{username} was disabled. Stopping...")
                        self.stop_account(username)
                        proc_obj.status = "disabled"
                        actions_taken.append(f"disabled:@{username}")
                    elif not was_enabled and now_enabled:
                        logger.info(f"Config reload: Account @{username} was enabled. Starting...")
                        self.start_account(username)
                        actions_taken.append(f"enabled_and_started:@{username}")
                else:
                    # 3. Completely new account
                    logger.info(f"Config reload: New account @{username} detected.")
                    new_proc = AccountProcess(
                        username=acc_cfg.username,
                        config_path=acc_cfg.config_path,
                        device_id=acc_cfg.device_id,
                        enabled=acc_cfg.enabled,
                        priority=acc_cfg.priority,
                        status="stopped" if acc_cfg.enabled else "disabled",
                    )
                    self.processes[username] = new_proc
                    if acc_cfg.enabled:
                        self.start_account(username)
                        actions_taken.append(f"added_and_started:@{username}")
                    else:
                        actions_taken.append(f"added_disabled:@{username}")

            self.config = new_config

        msg = f"Config reloaded successfully. Actions: {', '.join(actions_taken) if actions_taken else 'none'}"
        logger.info(msg)
        return {"status": "ok", "actions": actions_taken, "message": msg}

    @staticmethod
    def _compute_stagger_delay(stagger_range: str) -> float:
        """Computes random stagger delay within range."""
        if "-" in stagger_range:
            parts = stagger_range.split("-")
            try:
                min_v = float(parts[0].strip())
                max_v = float(parts[1].strip())
                return random.uniform(min_v, max_v)
            except Exception:
                return 30.0
        try:
            return float(stagger_range.strip())
        except Exception:
            return 30.0

    def _start_monitor_thread(self) -> None:
        """Starts background process monitoring daemon."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="OrchestratorProcessMonitor",
        )
        self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        """Background loop inspecting process return codes every 5 seconds."""
        while not self._stop_event.is_set():
            with self._lock:
                for username, proc_obj in self.processes.items():
                    if proc_obj.process and proc_obj.process.poll() is not None:
                        exit_code = proc_obj.process.returncode
                        if proc_obj.status == "running":
                            if exit_code == 0:
                                proc_obj.status = "stopped"
                                logger.info(f"Account @{username} (PID: {proc_obj.pid}) exited cleanly (code 0).")
                            else:
                                proc_obj.status = "crashed"
                                proc_obj.last_error = f"Exited with return code {exit_code}"
                                logger.warning(
                                    f"Account @{username} (PID: {proc_obj.pid}) exited unexpectedly with code {exit_code}!"
                                )

            self._stop_event.wait(5.0)

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Returns consolidated dictionary of all accounts' process status."""
        from InstaAddict.core.beacon import BeaconReader

        with self._lock:
            statuses = {}
            for username, proc in self.processes.items():
                beacon = BeaconReader.read_beacon(username)
                statuses[username] = {
                    "username": username,
                    "device": proc.device_id,
                    "enabled": proc.enabled,
                    "status": proc.status,
                    "pid": proc.pid if (proc.process and proc.process.poll() is None) else None,
                    "restarts": proc.restart_count,
                    "started_at": proc.started_at.isoformat() if proc.started_at else None,
                    "beacon": beacon,
                }
            return statuses

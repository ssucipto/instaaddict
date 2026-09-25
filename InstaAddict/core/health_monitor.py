import logging
import os
import queue
import random
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from InstaAddict.core.beacon import BeaconReader
from InstaAddict.core.orchestrator import AccountOrchestrator, AccountProcess

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Autonomous health monitoring and auto-recovery daemon for AccountOrchestrator.
    Features:
    - Periodically inspects bot process liveness, beacon freshness, and device responsiveness
    - Distinguishes intentional safety limit exits (status: 'limit_reached') to prevent restart loops (GAP-12)
    - Enforces serialized auto-recovery queue with 15s gap and randomized jitter to prevent thundering herd crashes (GAP-18)
    - Verifies device boot completion before attempting restart (GAP-16)
    - Targeted adb reconnect without global adb kill-server (GAP-08)
    - Rate-limits auto-restarts within rolling 1-hour window (max_restart_attempts)
    """

    STALE_THRESHOLD_SECONDS = 45.0
    CONFIRMED_STALE_SECONDS = 90.0
    MIN_RESTART_GAP_SECONDS = 15.0  # GAP-18: Minimum gap between consecutive account recoveries

    def __init__(self, orchestrator: AccountOrchestrator, check_interval: Optional[int] = None):
        self.orchestrator = orchestrator
        self.check_interval = check_interval or orchestrator.config.orchestrator.health_check_interval
        self.auto_restart_enabled = orchestrator.config.orchestrator.auto_restart
        self.max_restarts = orchestrator.config.orchestrator.max_restart_attempts

        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._recovery_thread: Optional[threading.Thread] = None
        self._recovery_queue: queue.Queue = queue.Queue()
        self._enqueued_users: set = set()
        self._recovery_lock = threading.Lock()

        # Rolling 1-hour restart history per account: {username: [timestamp, ...]}
        self.restart_history: Dict[str, List[datetime]] = {}
        self.recovery_events: List[Dict[str, Any]] = []

    def start(self) -> None:
        """Starts monitoring and recovery daemon threads."""
        self._stop_event.clear()

        self._recovery_thread = threading.Thread(
            target=self._recovery_worker_loop,
            daemon=True,
            name="HealthRecoveryWorker",
        )
        self._recovery_thread.start()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="HealthMonitorLoop",
        )
        self._monitor_thread.start()
        logger.info(f"HealthMonitor started (poll interval: {self.check_interval}s, auto-restart: {self.auto_restart_enabled})")

    def stop(self) -> None:
        """Stops monitor and recovery threads."""
        self._stop_event.set()
        self._recovery_queue.put(None)  # Sentinel to unblock recovery worker
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        if self._recovery_thread and self._recovery_thread.is_alive():
            self._recovery_thread.join(timeout=2)
        logger.info("HealthMonitor stopped.")

    def _monitor_loop(self) -> None:
        """Main periodic health inspection loop."""
        while not self._stop_event.is_set():
            try:
                self.inspect_fleet_health()
            except Exception as e:
                logger.error(f"Error in HealthMonitor loop: {e}")

            self._stop_event.wait(self.check_interval)

    def inspect_fleet_health(self) -> Dict[str, str]:
        """Inspects all managed accounts and classifies their health status."""
        health_results = {}
        for username, proc in list(self.orchestrator.processes.items()):
            if not proc.enabled:
                health_results[username] = "disabled"
                continue

            health_state = self.evaluate_account_health(proc)
            health_results[username] = health_state

            if self.auto_restart_enabled and health_state in ("CRASHED", "STALE_CONFIRMED", "DEVICE_OFFLINE"):
                self._enqueue_recovery(username, health_state)

        return health_results

    def evaluate_account_health(self, proc: AccountProcess) -> str:
        """Evaluates health of a single account process."""
        beacon = BeaconReader.read_beacon(proc.username)

        # 1. Process termination check
        if proc.process is None or proc.process.poll() is not None:
            # Check if exit was due to safety limits (GAP-12)
            if beacon and beacon.get("status") == "limit_reached":
                proc.status = "limit_reached"
                return "COMPLETED_LIMIT"

            if proc.status == "stopped":
                return "STOPPED"

            proc.status = "crashed"
            return "CRASHED"

        # 2. Process is alive — check beacon staleness
        if BeaconReader.is_beacon_stale(beacon, threshold_seconds=self.CONFIRMED_STALE_SECONDS):
            proc.status = "crashed"
            return "STALE_CONFIRMED"

        if BeaconReader.is_beacon_stale(beacon, threshold_seconds=self.STALE_THRESHOLD_SECONDS):
            return "STALE_WARNING"

        # 3. Check device readiness
        is_ready, reason = self.orchestrator.check_device_readiness(proc.device_id)
        if not is_ready:
            if reason == "DEVICE_BOOTING":
                proc.status = "device_booting"
                return "DEVICE_BOOTING"
            proc.status = "device_offline"
            return "DEVICE_OFFLINE"

        proc.status = "running"
        return "HEALTHY"

    def _enqueue_recovery(self, username: str, reason: str) -> None:
        """Enqueues an account into the serialized recovery queue (GAP-18)."""
        with self._recovery_lock:
            if username in self._enqueued_users:
                return

            # Check rate limiting: max restarts in rolling 1-hour window
            if not self._can_restart_account(username):
                logger.warning(
                    f"Account @{username} exceeded max restart attempts ({self.max_restarts}/hr). "
                    f"Transitioning to PAUSED_FAULT to prevent restart crash loops."
                )
                proc = self.orchestrator.processes.get(username)
                if proc:
                    proc.status = "paused_fault"
                return

            self._enqueued_users.add(username)
            self._recovery_queue.put((username, reason))
            logger.info(f"Enqueued auto-recovery for @{username} (Reason: {reason})")

    def _can_restart_account(self, username: str) -> bool:
        """Checks if account restart count within last hour is under max_restart_attempts."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        history = self.restart_history.setdefault(username, [])
        # Prune older than 1 hour
        self.restart_history[username] = [t for t in history if t > one_hour_ago]

        return len(self.restart_history[username]) < self.max_restarts

    def _record_restart(self, username: str) -> None:
        """Records an account restart timestamp."""
        now = datetime.now()
        self.restart_history.setdefault(username, []).append(now)

    def _recovery_worker_loop(self) -> None:
        """
        Worker thread executing serialized recoveries with a minimum 15-second gap
        and randomized exponential backoff jitter to prevent thundering herd storms (GAP-18).
        """
        while not self._stop_event.is_set():
            try:
                item = self._recovery_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if item is None:
                break

            username, reason = item
            try:
                self._execute_account_recovery(username, reason)
            except Exception as e:
                logger.error(f"Error during recovery of @{username}: {e}")
            finally:
                with self._recovery_lock:
                    self._enqueued_users.discard(username)

            # GAP-18: Minimum 15-second gap + randomized jitter between consecutive recoveries
            jitter = random.uniform(5.0, 15.0)
            delay = self.MIN_RESTART_GAP_SECONDS + jitter
            logger.info(f"Thundering herd guard: Waiting {delay:.1f}s before next potential recovery...")
            self._stop_event.wait(delay)

    def _execute_account_recovery(self, username: str, reason: str) -> bool:
        """Executes targeted recovery actions for an account."""
        logger.info(f"Executing autonomous recovery for @{username} (Trigger: {reason})...")
        proc = self.orchestrator.processes.get(username)
        if not proc:
            return False

        # If device offline, execute targeted reconnect without global adb kill-server (GAP-08)
        if reason == "DEVICE_OFFLINE":
            logger.info(f"Attempting targeted reconnect for device {proc.device_id}...")
            try:
                subprocess.run(["adb", "-s", proc.device_id, "reconnect"], capture_output=True, timeout=10)
                time.sleep(2)
                subprocess.run(["adb", "-s", proc.device_id, "reconnect", "device"], capture_output=True, timeout=10)
                time.sleep(3)
            except Exception as e:
                logger.debug(f"Targeted reconnect error: {e}")

        # Check boot completion property before launching bot (GAP-16)
        is_ready, state = self.orchestrator.check_device_readiness(proc.device_id)
        if not is_ready:
            logger.warning(f"Device {proc.device_id} for @{username} is not ready ({state}). Aborting restart.")
            proc.status = "device_offline" if "OFFLINE" in state else "device_booting"
            return False

        self._record_restart(username)
        success = self.orchestrator.restart_account(username, delay_seconds=2.0)

        event = {
            "timestamp": datetime.now().isoformat(),
            "username": username,
            "device": proc.device_id,
            "reason": reason,
            "success": success,
        }
        self.recovery_events.append(event)
        return success

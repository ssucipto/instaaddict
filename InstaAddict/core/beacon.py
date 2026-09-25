import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ACTIVE_BEACON_WRITER: Optional["StatusBeaconWriter"] = None


def get_active_beacon_writer() -> Optional["StatusBeaconWriter"]:
    return _ACTIVE_BEACON_WRITER


def set_active_beacon_writer(writer: Optional["StatusBeaconWriter"]) -> None:
    global _ACTIVE_BEACON_WRITER
    _ACTIVE_BEACON_WRITER = writer


class StatusBeaconWriter(threading.Thread):
    """
    Background daemon thread that periodically serializes active bot session status
    and KPIs into accounts/<username>/.status.json via atomic disk writes.
    Also monitors for the presence of accounts/<username>/.stop sentinel for graceful shutdown.
    """

    def __init__(self, username: str, interval: float = 10.0, account_dir: Optional[str] = None):
        super().__init__(daemon=True, name=f"StatusBeaconWriter-{username}")
        self.username = username
        self.interval = interval
        self.account_dir = account_dir or os.path.join("accounts", username)
        self.beacon_file = os.path.join(self.account_dir, ".status.json")
        self.stop_sentinel = os.path.join(self.account_dir, ".stop")
        self._stop_event = threading.Event()
        self._custom_status: Optional[str] = None
        self._device_info: Dict[str, Any] = {}
        self.start_time = datetime.now()
        self.stop_requested_callback = None

    def set_status(self, status: str) -> None:
        """Sets an explicit status override (e.g. 'starting', 'sleeping', 'limit_reached', 'stopped')."""
        self._custom_status = status
        self.write_beacon_now()

    def set_device_info(self, info: Dict[str, Any]) -> None:
        """Updates device telemetry dictionary."""
        self._device_info = info

    def stop(self) -> None:
        """Signals the beacon writer thread to terminate."""
        self._stop_event.set()

    def run(self) -> None:
        """Main loop writing beacon periodically and checking for .stop sentinel."""
        while not self._stop_event.is_set():
            try:
                self.write_beacon_now()
                self._check_stop_sentinel()
            except Exception as e:
                logger.debug(f"StatusBeaconWriter loop error: {e}")

            self._stop_event.wait(self.interval)

        # Write final stopped status beacon before exiting
        try:
            self._custom_status = self._custom_status or "stopped"
            self.write_beacon_now()
        except Exception:
            pass

    def _check_stop_sentinel(self) -> None:
        """Checks if orchestrator wrote .stop sentinel requesting clean exit."""
        if os.path.exists(self.stop_sentinel):
            logger.info(f"Detected stop sentinel at {self.stop_sentinel}. Initiating graceful bot shutdown...")
            if callable(self.stop_requested_callback):
                try:
                    self.stop_requested_callback()
                except Exception as e:
                    logger.debug(f"Error in stop_requested_callback: {e}")

    def write_beacon_now(self) -> None:
        """Gathers latest session telemetry and writes atomically to .status.json."""
        os.makedirs(self.account_dir, exist_ok=True)
        payload = self._build_payload()

        # Atomic write pattern: write to tmp file in same directory, then rename
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self.account_dir, prefix=".status_tmp_")
        try:
            with open(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
            # os.replace is atomic on both POSIX and Windows NTFS
            os.replace(tmp_path, self.beacon_file)
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            logger.debug(f"Failed to write atomic status beacon: {e}")

    def _build_payload(self) -> Dict[str, Any]:
        """Collects metrics from SessionState and creates dictionary payload."""
        from InstaAddict.core.session_state import SessionState

        session = SessionState.get_active()

        # Compute status
        status = self._custom_status or "running"

        total_likes = 0
        total_follows = 0
        total_comments = 0
        total_watched = 0
        total_crashes = 0
        total_unfollowed = 0
        session_index = 1
        current_job = "idle"

        if session is not None:
            total_likes = getattr(session, "totalLikes", 0)
            tf = getattr(session, "totalFollowed", {})
            total_follows = sum(tf.values()) if isinstance(tf, dict) else (tf if isinstance(tf, int) else 0)
            total_comments = getattr(session, "totalComments", 0)
            total_watched = getattr(session, "totalWatched", 0)
            total_crashes = getattr(session, "total_crashes", 0)
            total_unfollowed = getattr(session, "totalUnfollowed", 0)

            # Check if limits reached
            if getattr(session, "end_reached", False) or getattr(session, "target_reached", False):
                status = "limit_reached"

        uptime_seconds = int((datetime.now() - self.start_time).total_seconds())

        return {
            "username": self.username,
            "pid": os.getpid(),
            "status": status,
            "session_index": session_index,
            "uptime_seconds": uptime_seconds,
            "heartbeat": datetime.now().isoformat(),
            "current_job": current_job,
            "metrics": {
                "total_likes": total_likes,
                "total_follows": total_follows,
                "total_comments": total_comments,
                "total_watched": total_watched,
                "total_crashes": total_crashes,
                "total_unfollowed": total_unfollowed,
                "started_at": self.start_time.isoformat(),
            },
            "device": self._device_info,
            "errors": [],
        }


class BeaconReader:
    """Reads and parses status beacons written by StatusBeaconWriter with file-lock resilience."""

    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def read_beacon(
        cls, username: str, accounts_base_dir: str = "accounts", retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Reads accounts/<username>/.status.json with a 3-attempt retry loop and 10ms backoff
        to tolerate Windows NTFS file-lock contention (PermissionError/SharingViolation).
        Falls back to in-memory cached beacon if available.
        """
        clean_user = username.lstrip("@").strip()
        beacon_path = os.path.join(accounts_base_dir, clean_user, ".status.json")

        if not os.path.exists(beacon_path):
            return cls._cache.get(clean_user)

        last_err = None
        for attempt in range(retries):
            try:
                with open(beacon_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    cls._cache[clean_user] = data
                    return data
            except (PermissionError, FileNotFoundError, json.JSONDecodeError) as e:
                last_err = e
                time.sleep(0.01)  # 10ms backoff
            except Exception as e:
                last_err = e
                break

        # If read failed, return cached data
        if clean_user in cls._cache:
            return cls._cache[clean_user]

        return None

    @classmethod
    def read_all_beacons(
        cls, usernames: List[str], accounts_base_dir: str = "accounts"
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Reads beacons for all provided usernames."""
        results = {}
        for u in usernames:
            results[u] = cls.read_beacon(u, accounts_base_dir=accounts_base_dir)
        return results

    @classmethod
    def is_beacon_stale(
        cls, beacon: Optional[Dict[str, Any]], threshold_seconds: float = 45.0
    ) -> bool:
        """Determines if a beacon heartbeat timestamp is older than threshold_seconds."""
        if not beacon or not isinstance(beacon, dict):
            return True

        hb_str = beacon.get("heartbeat")
        if not hb_str:
            return True

        try:
            # Handle ISO formats
            hb = datetime.fromisoformat(str(hb_str))
            age = (datetime.now() - hb).total_seconds()
            return age > threshold_seconds
        except Exception:
            return True

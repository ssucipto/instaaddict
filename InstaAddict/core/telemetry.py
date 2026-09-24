import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Thread-safe, high-resolution latency profiler tracking execution duration across

    UI transitions, RPC calls, network requests, and device gestures.
    """

    _instance: Optional["PerformanceTracker"] = None
    _class_lock: threading.Lock = threading.Lock()

    def __init__(self):
        self._lock = threading.RLock()
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self.operation_counts: Dict[str, int] = defaultdict(int)
        self.operation_errors: Dict[str, int] = defaultdict(int)
        self.total_swipes: int = 0
        self.displaced_swipes: int = 0
        self.zero_displacement_swipes: int = 0
        self.snapback_events: int = 0
        self.adaptive_scale_factor: float = 1.0
        self.device_health_samples: deque = deque(maxlen=100)

    @classmethod
    def get_instance(cls) -> "PerformanceTracker":
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for unit test isolation)."""
        with cls._class_lock:
            cls._instance = None

    @contextmanager
    def measure(self, category: str, operation: str):
        """Context manager measuring execution duration in milliseconds."""
        key = f"{category}.{operation}"
        start = time.perf_counter()
        with self._lock:
            self.operation_counts[key] += 1
        try:
            yield
        except Exception:
            with self._lock:
                self.operation_errors[key] += 1
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            with self._lock:
                self.metrics[key].append(elapsed_ms)

    def record_metric(self, category: str, operation: str, duration_ms: float, error: bool = False):
        """Directly record an externally measured duration."""
        key = f"{category}.{operation}"
        with self._lock:
            self.operation_counts[key] += 1
            if error:
                self.operation_errors[key] += 1
            self.metrics[key].append(float(duration_ms))

    def record_swipe_motion(self, displaced: bool, snapback: bool = False):
        """Record viewport swipe motion displacement."""
        with self._lock:
            self.total_swipes += 1
            if displaced:
                self.displaced_swipes += 1
                # Restore adaptive scale towards 1.0 on success
                self.adaptive_scale_factor = max(1.0, self.adaptive_scale_factor * 0.95)
            else:
                self.zero_displacement_swipes += 1
                # Boost scale factor dynamically to escape sticky boundaries
                self.adaptive_scale_factor = min(1.5, self.adaptive_scale_factor * 1.15)

            if snapback:
                self.snapback_events += 1

    def record_device_health(self, connected: bool, latency_ms: float = 0.0):
        """Record device RPC connectivity sample and latency."""
        with self._lock:
            self.device_health_samples.append((time.time(), connected, float(latency_ms)))
            self.record_metric("device", "rpc_ping", latency_ms, error=not connected)

    def get_device_health(self) -> Dict[str, Any]:
        """Return device connectivity and transport latency summary."""
        with self._lock:
            samples = list(self.device_health_samples)
            if not samples:
                return {
                    "total_samples": 0,
                    "connected_pct": 100.0,
                    "avg_latency_ms": 0.0,
                    "latest_latency_ms": 0.0,
                    "is_healthy": True,
                }
            total = len(samples)
            connected_count = sum(1 for _, conn, _ in samples if conn)
            latencies = [lat for _, conn, lat in samples if conn and lat > 0.0]
            avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
            latest = samples[-1]
            conn_pct = (connected_count / total) * 100.0
            return {
                "total_samples": total,
                "connected_pct": round(conn_pct, 1),
                "avg_latency_ms": round(avg_lat, 1),
                "latest_latency_ms": round(latest[2], 1),
                "is_healthy": conn_pct >= 90.0,
            }

    def get_motion_summary(self) -> Dict[str, Any]:
        """Return motion displacement efficiency summary."""
        with self._lock:
            total = self.total_swipes
            disp = self.displaced_swipes
            zero = self.zero_displacement_swipes
            snap = self.snapback_events
            eff_pct = (disp / max(total, 1)) * 100.0 if total > 0 else 100.0
            return {
                "total_swipes": total,
                "displaced_swipes": disp,
                "zero_displacement_swipes": zero,
                "snapback_events": snap,
                "displacement_efficiency_pct": round(eff_pct, 1),
                "adaptive_scale_factor": round(self.adaptive_scale_factor, 2),
            }

    def get_percentiles(self) -> Dict[str, Dict[str, float]]:
        """Return P50 and P95 latency percentiles per operation."""
        summary = {}
        with self._lock:
            all_keys = set(self.metrics.keys()) | set(self.operation_counts.keys())
            for key in all_keys:
                durations = self.metrics.get(key, [])
                if not durations:
                    summary[key] = {"p50": 0.0, "p95": 0.0, "avg": 0.0}
                    continue
                sorted_d = sorted(durations)
                n = len(sorted_d)
                p50 = sorted_d[int(n * 0.50)]
                p95 = sorted_d[min(int(n * 0.95), n - 1)]
                avg = sum(sorted_d) / n
                summary[key] = {
                    "p50": round(p50, 1),
                    "p95": round(p95, 1),
                    "avg": round(avg, 1),
                }
        return summary

    def get_summary(self) -> Dict[str, Any]:
        """Return complete performance telemetry report."""
        summary = {}
        with self._lock:
            all_keys = set(self.metrics.keys()) | set(self.operation_counts.keys())
            for key in all_keys:
                durations = self.metrics.get(key, [])
                if not durations:
                    summary[key] = {
                        "count": self.operation_counts.get(key, 0),
                        "errors": self.operation_errors.get(key, 0),
                        "avg_ms": 0.0,
                        "p50_ms": 0.0,
                        "p95_ms": 0.0,
                        "min_ms": 0.0,
                        "max_ms": 0.0,
                    }
                    continue
                sorted_d = sorted(durations)
                n = len(sorted_d)
                p50 = sorted_d[int(n * 0.50)]
                p95 = sorted_d[min(int(n * 0.95), n - 1)]
                avg = sum(sorted_d) / n
                summary[key] = {
                    "count": self.operation_counts.get(key, 0),
                    "errors": self.operation_errors.get(key, 0),
                    "avg_ms": round(avg, 1),
                    "p50_ms": round(p50, 1),
                    "p95_ms": round(p95, 1),
                    "min_ms": round(sorted_d[0], 1),
                    "max_ms": round(sorted_d[-1], 1),
                }
        return summary


class MicroStallSentinel:
    """Detects early micro-stalls and repetitive UI timeouts (within 15-20s)

    to execute soft escapes far ahead of the 90s BotWatchdog daemon.
    """

    def __init__(self, timeout_threshold: int = 3, stagnation_seconds: float = 20.0):
        self.timeout_threshold = timeout_threshold
        self.stagnation_seconds = stagnation_seconds
        self.consecutive_timeouts = 0
        self.last_progress_time = time.time()
        self._lock = threading.RLock()

    def record_timeout(self, context: str = "") -> bool:
        """Record a UI element timeout. Returns True if micro-stall threshold breached."""
        with self._lock:
            self.consecutive_timeouts += 1
            stagnation = time.time() - self.last_progress_time
            if self.consecutive_timeouts >= self.timeout_threshold or stagnation >= self.stagnation_seconds:
                logger.warning(
                    f"[STALL-SENTINEL] Micro-stall detected ({self.consecutive_timeouts} consecutive timeouts, "
                    f"{stagnation:.1f}s stagnation on '{context}'). Triggering proactive soft recovery..."
                )
                self.reset()
                return True
            return False

    def record_progress(self):
        """Record successful UI progression, resetting timeout counter."""
        with self._lock:
            self.consecutive_timeouts = 0
            self.last_progress_time = time.time()

    def reset(self):
        """Reset sentinel state."""
        with self._lock:
            self.consecutive_timeouts = 0
            self.last_progress_time = time.time()

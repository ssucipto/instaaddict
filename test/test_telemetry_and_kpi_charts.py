import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from rich.console import Console

from InstaAddict.core.dogfood import DogfoodOptimizer
from InstaAddict.core.session_state import SessionState, SessionStateEncoder
from InstaAddict.core.telemetry import MicroStallSentinel, PerformanceTracker
from InstaAddict.core.tui import (
    DashboardManager,
    KeyboardListenerThread,
    ViewMode,
    safe_bar,
)


class TestPerformanceTracker(unittest.TestCase):
    def setUp(self):
        PerformanceTracker.reset_instance()
        self.tracker = PerformanceTracker.get_instance()

    def tearDown(self):
        PerformanceTracker.reset_instance()

    def test_singleton_identity(self):
        t2 = PerformanceTracker.get_instance()
        self.assertIs(self.tracker, t2)

    def test_measure_context_manager_and_percentiles(self):
        with self.tracker.measure("test_cat", "op_fast"):
            time.sleep(0.01)

        summary = self.tracker.get_summary()
        self.assertIn("test_cat.op_fast", summary)
        op_stat = summary["test_cat.op_fast"]
        self.assertEqual(op_stat["count"], 1)
        self.assertEqual(op_stat["errors"], 0)
        self.assertGreater(op_stat["avg_ms"], 5.0)

        percentiles = self.tracker.get_percentiles()
        self.assertIn("test_cat.op_fast", percentiles)
        self.assertGreater(percentiles["test_cat.op_fast"]["p50"], 5.0)
        self.assertGreater(percentiles["test_cat.op_fast"]["p95"], 5.0)

    def test_measure_records_exception(self):
        with self.assertRaises(ValueError):
            with self.tracker.measure("test_cat", "op_error"):
                raise ValueError("Simulated failure")

        summary = self.tracker.get_summary()
        self.assertEqual(summary["test_cat.op_error"]["count"], 1)
        self.assertEqual(summary["test_cat.op_error"]["errors"], 1)

    def test_zero_samples_defensive(self):
        self.tracker.operation_counts["uncalled"] = 0
        summary = self.tracker.get_summary()
        self.assertIn("uncalled", summary)
        self.assertEqual(summary["uncalled"]["avg_ms"], 0.0)
        self.assertEqual(summary["uncalled"]["p50_ms"], 0.0)

        pct = self.tracker.get_percentiles()
        self.assertEqual(pct["uncalled"]["p50"], 0.0)

    def test_record_swipe_motion_and_adaptive_scale(self):
        self.tracker.record_swipe_motion(displaced=True)
        self.assertEqual(self.tracker.total_swipes, 1)
        self.assertEqual(self.tracker.displaced_swipes, 1)
        self.assertEqual(self.tracker.zero_displacement_swipes, 0)
        self.assertEqual(self.tracker.adaptive_scale_factor, 1.0)

        # Zero displacement boosts scale factor
        self.tracker.record_swipe_motion(displaced=False, snapback=True)
        self.assertEqual(self.tracker.total_swipes, 2)
        self.assertEqual(self.tracker.zero_displacement_swipes, 1)
        self.assertEqual(self.tracker.snapback_events, 1)
        self.assertGreater(self.tracker.adaptive_scale_factor, 1.0)

        motion_sum = self.tracker.get_motion_summary()
        self.assertEqual(motion_sum["displacement_efficiency_pct"], 50.0)
        self.assertEqual(motion_sum["total_swipes"], 2)


class TestMicroStallSentinel(unittest.TestCase):
    def test_timeout_threshold_trigger(self):
        sentinel = MicroStallSentinel(
            timeout_threshold=3, stagnation_seconds=20.0
        )
        self.assertFalse(sentinel.record_timeout("button_1"))
        self.assertFalse(sentinel.record_timeout("button_2"))
        # 3rd consecutive timeout triggers micro-stall
        self.assertTrue(sentinel.record_timeout("button_3"))
        # Resets counter after trigger
        self.assertEqual(sentinel.consecutive_timeouts, 0)

    def test_progress_resets_counter(self):
        sentinel = MicroStallSentinel(
            timeout_threshold=3, stagnation_seconds=20.0
        )
        self.assertFalse(sentinel.record_timeout("button_1"))
        self.assertFalse(sentinel.record_timeout("button_2"))
        sentinel.record_progress()
        self.assertEqual(sentinel.consecutive_timeouts, 0)
        self.assertFalse(sentinel.record_timeout("button_1"))


class TestSessionStateTelemetry(unittest.TestCase):
    def test_session_state_motion_increments(self):
        session = SessionState()
        session.increment_swipes(2)
        self.assertEqual(session.totalSwipes, 2)

        session.increment_zero_displacement(1)
        self.assertEqual(session.zeroDisplacementSwipes, 1)

        session.increment_snapback_events(1)
        self.assertEqual(session.snapbackEvents, 1)

        session.increment_micro_stall_escapes(1)
        self.assertEqual(session.totalMicroStallEscapes, 1)

        session.update_durations(
            {"view.profile": 500.0}, {"view.profile": 1200.0}
        )
        self.assertEqual(session.durationsP50["view.profile"], 500.0)
        self.assertEqual(session.durationsP95["view.profile"], 1200.0)

    def test_session_state_encoder_serialization(self):
        session = SessionState()
        session.increment_swipes(5)
        session.increment_zero_displacement(2)
        session.increment_snapback_events(1)
        session.increment_micro_stall_escapes(3)
        session.update_durations({"test": 100}, {"test": 200})

        encoded = json.dumps(session, cls=SessionStateEncoder)
        data = json.loads(encoded)

        self.assertEqual(data["total_swipes"], 5)
        self.assertEqual(data["zero_displacement_swipes"], 2)
        self.assertEqual(data["snapback_events"], 1)
        self.assertEqual(data["total_micro_stall_escapes"], 3)
        self.assertEqual(data["durations_p50"]["test"], 100)
        self.assertEqual(data["durations_p95"]["test"], 200)


class TestSafeBarAndUnicodeHandling(unittest.TestCase):
    def test_safe_bar_clamping(self):
        bar_zero = safe_bar(0.0, width=10)
        self.assertIn(" ", bar_zero.plain)
        self.assertNotIn("█", bar_zero.plain)

        bar_full = safe_bar(1.0, width=10)
        self.assertEqual(bar_full.plain.strip(), "█" * 10)

        # Clamping beyond 0.0 and 1.0
        bar_neg = safe_bar(-0.5, width=10)
        self.assertNotIn("█", bar_neg.plain)

        bar_over = safe_bar(1.5, width=10)
        self.assertEqual(bar_over.plain.strip(), "█" * 10)

    @patch("sys.stdout")
    def test_safe_bar_ascii_fallback(self, mock_stdout):
        mock_stdout.encoding = "cp1252"
        bar = safe_bar(0.5, width=10)
        plain = bar.plain
        self.assertIn("#", plain)
        self.assertIn("-", plain)
        self.assertNotIn("█", plain)


class TestTuiKeyboardAndKpiCharts(unittest.TestCase):
    def setUp(self):
        self.console = Console(force_terminal=True, width=120, height=35)
        self.manager = DashboardManager(console=self.console)

    def test_view_mode_toggle_via_shortcut(self):
        self.assertEqual(self.manager.view_mode, ViewMode.LIVE_DASHBOARD)
        listener = KeyboardListenerThread(self.manager)

        # 1st press: LIVE -> CHARTS
        listener._handle_key(b"\x07")
        self.assertEqual(self.manager.view_mode, ViewMode.STATISTICS_CHARTS)

        # 2nd press: CHARTS -> FILTER_INTELLIGENCE
        listener._handle_key("g")
        self.assertEqual(self.manager.view_mode, ViewMode.FILTER_INTELLIGENCE)

        # 3rd press: FILTER_INTELLIGENCE -> LIVE (full cycle)
        listener._handle_key("G")
        self.assertEqual(self.manager.view_mode, ViewMode.LIVE_DASHBOARD)

    def test_kpi_charts_render_without_error(self):
        # Populate metrics in state
        s = self.manager.state
        s.username = "tester"
        s.posts_checked = 150
        s.profiles_checked = 60
        s.profiles_skipped = 20
        s.total_interactions = 35
        s.likes_count = 25
        s.follows_count = 5
        s.comments_count = 3
        s.watched_count = 10
        s.crashes_count = 0
        s.total_swipes = 40
        s.zero_displacement_swipes = 4
        s.snapback_events = 1
        s.micro_stall_escapes = 2

        # 1. Render funnel
        funnel_panel = self.manager._render_funnel_chart()
        self.assertIsNotNone(funnel_panel)

        # 2. Render quota gauges
        quota_panel = self.manager._render_quota_velocity_chart()
        self.assertIsNotNone(quota_panel)

        # 3. Render latency distribution
        latency_panel = self.manager._render_latency_chart()
        self.assertIsNotNone(latency_panel)

        # 4. Render motion health
        motion_panel = self.manager._render_motion_health_chart()
        self.assertIsNotNone(motion_panel)

        # 5. Full charts layout
        charts_layout = self.manager._render_charts_view()
        self.assertIsNotNone(charts_layout)

        # 6. Full Dashboard generate_layout in STATISTICS_CHARTS mode
        self.manager.view_mode = ViewMode.STATISTICS_CHARTS
        full_layout = self.manager.generate_layout()
        self.assertIsNotNone(full_layout)


class TestDogfoodAutoTune(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.username = "autotune_user"
        self.account_dir = os.path.join(
            self.test_dir, "accounts", self.username
        )
        os.makedirs(self.account_dir, exist_ok=True)
        self.config_path = os.path.join(self.account_dir, "config.yml")

        # Create sample config.yml with comments
        self.sample_yaml = (
            "# Bot configuration file\n"
            "username: autotune_user\n"
            "delay-mean: 2.0 # default delay\n"
            "reels_evaluate_percentage: 80 # evaluation rate\n"
            "speed: 2\n"
        )
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(self.sample_yaml)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_apply_tuning_preserves_comments_and_creates_backup(self):
        optimizer = DogfoodOptimizer(self.username)
        optimizer.account_dir = self.account_dir
        optimizer.config_path = self.config_path
        optimizer.suggestions_json_path = os.path.join(
            self.account_dir, "tuning_suggestions.json"
        )
        optimizer.suggestions_md_path = os.path.join(
            self.account_dir, "tuning_suggestions.md"
        )

        # Mock analyze to recommend delay-mean up and evaluate-pct down
        mock_analysis = {
            "recommendations": [
                {
                    "category": "Navigation",
                    "severity": "HIGH",
                    "parameter": "delay-mean",
                    "suggested_value": "increase by 1.0s",
                },
                {
                    "category": "Quota",
                    "severity": "HIGH",
                    "parameter": "reels_evaluate_percentage",
                    "suggested_value": "reduce by 15",
                },
            ]
        }

        with patch.object(optimizer, "analyze", return_value=mock_analysis):
            tune_res = optimizer.apply_tuning(dry_run=False, backup=True)

            self.assertEqual(len(tune_res["applied"]), 2)
            self.assertIsNotNone(tune_res["backup_file"])
            self.assertTrue(os.path.exists(tune_res["backup_file"]))

            # Verify modified config preserved comments
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("delay-mean: 3.0 # default delay", content)
            self.assertIn(
                "reels_evaluate_percentage: 65 # evaluation rate", content
            )
            self.assertIn("# Bot configuration file", content)

    def test_apply_tuning_clamping_limits(self):
        # Set extreme values
        extreme_yaml = (
            "delay-mean: 14.8\n"
            "reels_evaluate_percentage: 25\n"
        )
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(extreme_yaml)

        optimizer = DogfoodOptimizer(self.username)
        optimizer.account_dir = self.account_dir
        optimizer.config_path = self.config_path

        mock_analysis = {
            "recommendations": [
                {"parameter": "delay-mean"},
                {"parameter": "reels_evaluate_percentage"},
            ]
        }

        with patch.object(optimizer, "analyze", return_value=mock_analysis):
            optimizer.apply_tuning(dry_run=False, backup=False)

            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()

            # delay-mean clamped to 15.0 max
            self.assertIn("delay-mean: 15.0", content)
            # reels_evaluate_percentage clamped to 20 min
            self.assertIn("reels_evaluate_percentage: 20", content)


if __name__ == "__main__":
    unittest.main()

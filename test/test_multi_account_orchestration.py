import json
import os
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import yaml

from InstaAddict.core.beacon import BeaconReader, StatusBeaconWriter
from InstaAddict.core.health_monitor import HealthMonitor
from InstaAddict.core.multi_config import (
    MultiAccountConfig,
    MultiConfigValidationError,
)
from InstaAddict.core.multi_dashboard import MultiAccountDashboard
from InstaAddict.core.multi_telemetry import MultiAccountTelemetryAggregator
from InstaAddict.core.orchestrator import AccountOrchestrator


# ---------------------------------------------------------------------------
# Test Fixtures & Headless Mock Harness (GAP-17)
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_accounts_dir(tmp_path):
    """Creates a temporary accounts directory structure with mock config files."""
    acc_dir = tmp_path / "accounts"
    acc_dir.mkdir()

    # Create account 1
    acc1 = acc_dir / "user_alpha"
    acc1.mkdir()
    (acc1 / "config.yml").write_text("username: user_alpha\nworking-hours: 09:00-22:00\n", encoding="utf-8")

    # Create account 2
    acc2 = acc_dir / "user_beta"
    acc2.mkdir()
    (acc2 / "config.yml").write_text("username: user_beta\nworking-hours: 10:00-23:00\n", encoding="utf-8")

    return str(acc_dir)


@pytest.fixture
def sample_multi_config_file(tmp_path, temp_accounts_dir):
    """Creates a valid multi_config.yml in a temporary directory."""
    cfg_data = {
        "orchestrator": {
            "max_concurrent": 3,
            "stagger_start_seconds": "5-10",
            "health_check_interval": 5,
            "auto_restart": True,
            "max_restart_attempts": 3,
            "log_dir": str(tmp_path / "logs" / "orchestrator"),
        },
        "accounts": [
            {
                "username": "user_alpha",
                "config": os.path.join(temp_accounts_dir, "user_alpha", "config.yml"),
                "device": "emulator-5554",
                "enabled": True,
                "priority": 1,
                "gemini_api_key": "AIzaSy_MOCK_KEY_ALPHA",
            },
            {
                "username": "user_beta",
                "config": os.path.join(temp_accounts_dir, "user_beta", "config.yml"),
                "device": "emulator-5556",
                "enabled": True,
                "priority": 2,
            },
        ],
    }
    cfg_file = tmp_path / "multi_config.yml"
    cfg_file.write_text(yaml.dump(cfg_data), encoding="utf-8")
    return str(cfg_file)


# ---------------------------------------------------------------------------
# Task 42: MultiAccountConfig Tests
# ---------------------------------------------------------------------------

class TestMultiConfig:
    def test_load_valid_config(self, sample_multi_config_file):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        assert cfg.orchestrator.max_concurrent == 3
        assert cfg.orchestrator.stagger_start_seconds == "5-10"
        assert len(cfg.accounts) == 2

        enabled = cfg.get_enabled_accounts()
        assert len(enabled) == 2
        assert enabled[0].username == "user_alpha"
        assert enabled[0].gemini_api_key == "AIzaSy_MOCK_KEY_ALPHA"
        assert enabled[1].username == "user_beta"

    def test_missing_config_file_raises_error(self):
        with pytest.raises(FileNotFoundError):
            MultiAccountConfig.load("non_existent_file.yml")

    def test_duplicate_username_rejected(self, tmp_path, temp_accounts_dir):
        cfg_data = {
            "orchestrator": {},
            "accounts": [
                {
                    "username": "duplicate_user",
                    "config": os.path.join(temp_accounts_dir, "user_alpha", "config.yml"),
                    "device": "emulator-5554",
                },
                {
                    "username": "duplicate_user",
                    "config": os.path.join(temp_accounts_dir, "user_beta", "config.yml"),
                    "device": "emulator-5556",
                },
            ],
        }
        f = tmp_path / "dup_user.yml"
        f.write_text(yaml.dump(cfg_data), encoding="utf-8")
        with pytest.raises(MultiConfigValidationError, match="Duplicate username detected"):
            MultiAccountConfig.load(str(f))

    def test_duplicate_device_id_rejected(self, tmp_path, temp_accounts_dir):
        cfg_data = {
            "orchestrator": {},
            "accounts": [
                {
                    "username": "user1",
                    "config": os.path.join(temp_accounts_dir, "user_alpha", "config.yml"),
                    "device": "emulator-5554",
                    "enabled": True,
                },
                {
                    "username": "user2",
                    "config": os.path.join(temp_accounts_dir, "user_beta", "config.yml"),
                    "device": "emulator-5554",
                    "enabled": True,
                },
            ],
        }
        f = tmp_path / "dup_dev.yml"
        f.write_text(yaml.dump(cfg_data), encoding="utf-8")
        with pytest.raises(MultiConfigValidationError, match="Device collision"):
            MultiAccountConfig.load(str(f))

    def test_invalid_device_regex_rejected(self, tmp_path, temp_accounts_dir):
        cfg_data = {
            "orchestrator": {},
            "accounts": [
                {
                    "username": "user1",
                    "config": os.path.join(temp_accounts_dir, "user_alpha", "config.yml"),
                    "device": "bad/device/name",
                }
            ],
        }
        f = tmp_path / "bad_dev.yml"
        f.write_text(yaml.dump(cfg_data), encoding="utf-8")
        with pytest.raises(MultiConfigValidationError, match="invalid format"):
            MultiAccountConfig.load(str(f))

    def test_invalid_stagger_range_rejected(self, tmp_path, temp_accounts_dir):
        cfg_data = {
            "orchestrator": {"stagger_start_seconds": "50-10"},
            "accounts": [
                {
                    "username": "user1",
                    "config": os.path.join(temp_accounts_dir, "user_alpha", "config.yml"),
                    "device": "emulator-5554",
                }
            ],
        }
        f = tmp_path / "bad_stagger.yml"
        f.write_text(yaml.dump(cfg_data), encoding="utf-8")
        with pytest.raises(MultiConfigValidationError, match="min .* cannot be greater than max"):
            MultiAccountConfig.load(str(f))

    def test_missing_child_config_file_rejected(self, tmp_path):
        cfg_data = {
            "orchestrator": {},
            "accounts": [
                {
                    "username": "user1",
                    "config": "missing/config.yml",
                    "device": "emulator-5554",
                }
            ],
        }
        f = tmp_path / "missing_child.yml"
        f.write_text(yaml.dump(cfg_data), encoding="utf-8")
        with pytest.raises(MultiConfigValidationError, match="does not exist"):
            MultiAccountConfig.load(str(f))


# ---------------------------------------------------------------------------
# Task 44: StatusBeaconWriter & BeaconReader Tests
# ---------------------------------------------------------------------------

class TestStatusBeaconAndIPC:
    def test_beacon_writer_writes_valid_json(self, tmp_path):
        acc_dir = tmp_path / "test_user"
        acc_dir.mkdir()

        writer = StatusBeaconWriter("test_user", interval=0.1, account_dir=str(acc_dir))
        writer.write_beacon_now()

        beacon_path = acc_dir / ".status.json"
        assert beacon_path.exists()

        data = json.loads(beacon_path.read_text(encoding="utf-8"))
        assert data["username"] == "test_user"
        assert data["status"] == "running"
        assert "heartbeat" in data
        assert "metrics" in data
        assert data["pid"] == os.getpid()

    def test_beacon_reader_reads_and_caches(self, tmp_path):
        acc_dir = tmp_path / "test_user"
        acc_dir.mkdir()
        beacon_file = acc_dir / ".status.json"
        payload = {
            "username": "test_user",
            "status": "running",
            "heartbeat": datetime.now().isoformat(),
            "metrics": {"total_likes": 10, "total_follows": 3},
        }
        beacon_file.write_text(json.dumps(payload), encoding="utf-8")

        # Read beacon
        data = BeaconReader.read_beacon("test_user", accounts_base_dir=str(tmp_path))
        assert data is not None
        assert data["username"] == "test_user"
        assert data["metrics"]["total_likes"] == 10

        # Verify staleness check
        assert not BeaconReader.is_beacon_stale(data, threshold_seconds=10.0)

        # Stale beacon
        old_payload = {
            "username": "test_user",
            "heartbeat": (datetime.now() - timedelta(seconds=60)).isoformat(),
        }
        assert BeaconReader.is_beacon_stale(old_payload, threshold_seconds=45.0)

    def test_beacon_writer_detects_stop_sentinel(self, tmp_path):
        acc_dir = tmp_path / "test_user"
        acc_dir.mkdir()
        stop_file = acc_dir / ".stop"

        writer = StatusBeaconWriter("test_user", interval=0.1, account_dir=str(acc_dir))
        callback_called = threading.Event()
        writer.stop_requested_callback = lambda: callback_called.set()

        # Write stop sentinel
        stop_file.write_text("STOP\n", encoding="utf-8")
        writer._check_stop_sentinel()

        assert callback_called.is_set()


# ---------------------------------------------------------------------------
# Task 43: AccountOrchestrator Tests
# ---------------------------------------------------------------------------

class TestAccountOrchestrator:
    def test_pid_lock_acquisition_and_cleanup(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        pid_file = tmp_path / "test_orch.pid"

        with patch.object(AccountOrchestrator, "PID_FILE_PATH", str(pid_file)):
            orch = AccountOrchestrator(cfg, project_root=str(tmp_path))
            assert pid_file.exists()
            assert pid_file.read_text().strip() == str(os.getpid())

            # Cleanup
            orch._cleanup_on_exit()
            assert not pid_file.exists()

    def test_duplicate_orchestrator_raises_runtime_error(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        pid_file = tmp_path / "test_orch_dup.pid"

        # Pre-seed PID file with active current PID
        pid_file.write_text(str(os.getpid()), encoding="utf-8")

        with patch.object(AccountOrchestrator, "PID_FILE_PATH", str(pid_file)):
            with pytest.raises(RuntimeError, match="Another active AccountOrchestrator is already running"):
                AccountOrchestrator(cfg, project_root=str(tmp_path))

    def test_log_file_bounded_rotation(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))

        # Create large stdout log file (>10MB)
        log_dir = tmp_path / "logs" / "orchestrator"
        log_dir.mkdir(parents=True, exist_ok=True)
        large_log = log_dir / "user_alpha_stdout.log"
        # Write dummy bytes
        large_log.write_bytes(b"A" * (10 * 1024 * 1024 + 100))

        # Opening stdout file should rotate
        f = orch._open_stdout_file("user_alpha")
        f.close()

        backup_log = log_dir / "user_alpha_stdout.log.1"
        assert backup_log.exists()
        assert os.path.getsize(backup_log) > 10 * 1024 * 1024

    def test_device_readiness_checks(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))

        # Mock adb devices returning ready
        mock_adb = MagicMock()
        mock_adb.stdout = "List of devices attached\nemulator-5554\tdevice\n"
        mock_boot = MagicMock()
        mock_boot.stdout = "1\n"
        mock_anim = MagicMock()
        mock_anim.stdout = "stopped\n"

        with patch("subprocess.run", side_effect=[mock_adb, mock_boot, mock_anim]):
            ready, reason = orch.check_device_readiness("emulator-5554")
            assert ready is True
            assert reason == "READY"

        # Mock device offline
        mock_adb_offline = MagicMock()
        mock_adb_offline.stdout = "List of devices attached\nemulator-5554\toffline\n"
        with patch("subprocess.run", return_value=mock_adb_offline):
            ready, reason = orch.check_device_readiness("emulator-5554")
            assert ready is False
            assert reason == "DEVICE_OFFLINE"

        # Mock device still booting
        with patch("subprocess.run", side_effect=[mock_adb, MagicMock(stdout="0\n"), mock_anim]):
            ready, reason = orch.check_device_readiness("emulator-5554")
            assert ready is False
            assert reason == "DEVICE_BOOTING"

    def test_process_spawning_and_stop_account(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))

        # Mock device readiness
        orch.check_device_readiness = MagicMock(return_value=(True, "READY"))

        # Mock subprocess.Popen
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = None  # running

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            success = orch.start_account("user_alpha")
            assert success is True
            assert orch.processes["user_alpha"].status == "running"
            assert orch.processes["user_alpha"].pid == 9999

            # Verify environment variables injected
            _, kwargs = mock_popen.call_args
            env = kwargs["env"]
            assert env["INSTAADDICT_NO_TUI"] == "1"
            assert env["INSTAADDICT_NO_TELEGRAM_INBOX"] == "1"
            assert env["INSTAADDICT_MULTI_ACCOUNT"] == "1"
            assert env["GEMINI_API_KEY"] == "AIzaSy_MOCK_KEY_ALPHA"

            # Test stopping account
            mock_proc.poll.side_effect = [None, 0, 0, 0]  # First alive, then exited
            stop_res = orch.stop_account("user_alpha", timeout=1.0)
            assert stop_res is True
            assert orch.processes["user_alpha"].status == "stopped"

    def test_reload_config_zero_downtime(self, sample_multi_config_file, tmp_path, temp_accounts_dir):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))

        # Add third account to config file
        new_cfg_data = {
            "orchestrator": {"max_concurrent": 3},
            "accounts": [
                {
                    "username": "user_alpha",
                    "config": os.path.join(temp_accounts_dir, "user_alpha", "config.yml"),
                    "device": "emulator-5554",
                    "enabled": True,
                },
                {
                    "username": "user_beta",
                    "config": os.path.join(temp_accounts_dir, "user_beta", "config.yml"),
                    "device": "emulator-5556",
                    "enabled": False,  # disabled in reload
                },
            ],
        }
        with open(sample_multi_config_file, "w", encoding="utf-8") as f:
            yaml.dump(new_cfg_data, f)

        # Trigger reload_config
        with patch.object(orch, "stop_account") as mock_stop:
            res = orch.reload_config()
            assert res["status"] == "ok"
            assert "disabled:@user_beta" in res["actions"]
            mock_stop.assert_called_with("user_beta")


# ---------------------------------------------------------------------------
# Task 47: HealthMonitor Tests
# ---------------------------------------------------------------------------

class TestHealthMonitor:
    def test_health_monitor_detects_limit_reached_without_restart(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))
        hm = HealthMonitor(orch, check_interval=1)

        proc_alpha = orch.processes["user_alpha"]
        proc_alpha.process = None  # terminated

        # Mock beacon showing limit_reached
        mock_beacon = {"status": "limit_reached", "heartbeat": datetime.now().isoformat()}
        with patch.object(BeaconReader, "read_beacon", return_value=mock_beacon):
            state = hm.evaluate_account_health(proc_alpha)
            assert state == "COMPLETED_LIMIT"
            assert proc_alpha.status == "limit_reached"

    def test_health_monitor_enqueues_recovery_for_crash(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))
        hm = HealthMonitor(orch, check_interval=1)

        proc_alpha = orch.processes["user_alpha"]
        proc_alpha.status = "running"
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # crashed
        proc_alpha.process = mock_proc

        with patch.object(BeaconReader, "read_beacon", return_value=None):
            state = hm.evaluate_account_health(proc_alpha)
            assert state == "CRASHED"

            # Enqueue recovery
            hm._enqueue_recovery("user_alpha", "CRASHED")
            assert "user_alpha" in hm._enqueued_users

    def test_health_monitor_respects_max_restart_attempts(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))
        hm = HealthMonitor(orch, check_interval=1)
        hm.max_restarts = 2

        # Record 2 recent restarts
        hm._record_restart("user_alpha")
        hm._record_restart("user_alpha")

        assert hm._can_restart_account("user_alpha") is False


# ---------------------------------------------------------------------------
# Task 45: MultiAccountDashboard Tests
# ---------------------------------------------------------------------------

class TestMultiDashboard:
    def test_dashboard_renders_components_without_exceptions(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))
        dash = MultiAccountDashboard(orch)

        # Header
        header = dash.render_header()
        assert header is not None

        # Mode 1: Table
        table = dash.render_summary_table()
        assert table is not None
        assert len(table.rows) == 2

        # Mode 2: Cards
        cards = dash.render_detailed_cards()
        assert cards is not None

        # Mode 3: Telemetry
        funnel = dash.render_telemetry_funnel()
        assert funnel is not None

        # Full layout
        layout = dash.generate_layout()
        assert layout is not None

    def test_dashboard_key_handling(self, sample_multi_config_file, tmp_path):
        cfg = MultiAccountConfig.load(sample_multi_config_file)
        orch = AccountOrchestrator(cfg, project_root=str(tmp_path))
        dash = MultiAccountDashboard(orch)

        # Tab key cycles view modes 1 -> 2 -> 3 -> 1
        assert dash.view_mode == 1
        dash._handle_key(b"\t")
        assert dash.view_mode == 2
        dash._handle_key(b"\t")
        assert dash.view_mode == 3
        dash._handle_key(b"\t")
        assert dash.view_mode == 1

        # Hotkey [C] triggers reload
        with patch.object(orch, "reload_config", return_value={"status": "ok", "message": "reloaded"}):
            dash._handle_key(b"c")
            assert len(dash.event_log) > 0


# ---------------------------------------------------------------------------
# Task 48: MultiAccountTelemetry Tests
# ---------------------------------------------------------------------------

class TestMultiTelemetry:
    def test_fleet_telemetry_aggregation(self, tmp_path):
        acc_dir = tmp_path / "accounts"
        acc_dir.mkdir()

        # Seed account 1 sessions
        u1_dir = acc_dir / "user1"
        u1_dir.mkdir()
        u1_sessions = [
            {"totalLikes": 25, "totalFollowed": {"feed": 5}, "totalComments": 2, "totalWatched": 10, "total_crashes": 0}
        ]
        (u1_dir / "sessions.json").write_text(json.dumps(u1_sessions), encoding="utf-8")

        # Seed account 2 sessions
        u2_dir = acc_dir / "user2"
        u2_dir.mkdir()
        u2_sessions = [
            {"totalLikes": 15, "totalFollowed": {"feed": 3}, "totalComments": 1, "totalWatched": 5, "total_crashes": 1}
        ]
        (u2_dir / "sessions.json").write_text(json.dumps(u2_sessions), encoding="utf-8")

        agg = MultiAccountTelemetryAggregator(
            accounts=["user1", "user2"],
            accounts_base_dir=str(acc_dir),
            log_dir=str(tmp_path / "logs"),
        )
        data = agg.aggregate_fleet_telemetry()

        assert data["fleet_totals"]["total_likes"] == 40
        assert data["fleet_totals"]["total_follows"] == 8
        assert data["fleet_totals"]["total_comments"] == 3
        assert data["fleet_totals"]["total_watched"] == 15
        assert data["fleet_totals"]["total_crashes"] == 1

        # Report generation
        md_path, json_path = agg.generate_fleet_report()
        assert os.path.exists(md_path)
        assert os.path.exists(json_path)


# ---------------------------------------------------------------------------
# Task 46 & CLI: cmd_multi Tests
# ---------------------------------------------------------------------------

class TestMultiCLI:
    def test_cmd_multi_status_output(self, sample_multi_config_file, capsys):
        from InstaAddict.__main__ import cmd_multi

        args = MagicMock()
        args.config = sample_multi_config_file
        args.status = True
        args.stop = None
        args.reload = False
        args.only = None

        cmd_multi(args)
        captured = capsys.readouterr()
        assert "InstaAddict-AI Fleet Status" in captured.out
        assert "@user_alpha" in captured.out
        assert "@user_beta" in captured.out

    def test_cmd_multi_stop_single_account(self, tmp_path, monkeypatch):
        from InstaAddict.__main__ import cmd_multi

        monkeypatch.chdir(tmp_path)
        args = MagicMock()
        args.config = None
        args.status = False
        args.stop = "@user_alpha"
        args.reload = False
        args.only = None

        cmd_multi(args)
        stop_file = tmp_path / "accounts" / "user_alpha" / ".stop"
        assert stop_file.exists()
        assert "STOP" in stop_file.read_text(encoding="utf-8")

    def test_cmd_multi_reload_signal(self, tmp_path, monkeypatch, capsys):
        from InstaAddict.__main__ import cmd_multi

        monkeypatch.chdir(tmp_path)
        orch_dir = tmp_path / "logs" / "orchestrator"
        orch_dir.mkdir(parents=True, exist_ok=True)
        pid_file = orch_dir / "orchestrator.pid"
        pid_file.write_text(str(os.getpid()), encoding="utf-8")

        args = MagicMock()
        args.config = None
        args.status = False
        args.stop = None
        args.reload = True
        args.only = None

        cmd_multi(args)
        captured = capsys.readouterr()
        assert "Reload signal dispatched to running orchestrator" in captured.out
        cmd_file = orch_dir / ".cmd.json"
        assert cmd_file.exists()
        data = json.loads(cmd_file.read_text(encoding="utf-8"))
        assert data["cmd"] == "reload"

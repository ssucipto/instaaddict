import time
from unittest.mock import MagicMock, patch

import pytest

from InstaAddict.core.session_state import SessionState, SessionStateEncoder
from InstaAddict.core.tui import DashboardManager
from InstaAddict.core.watchdog import BotWatchdog


@pytest.fixture(autouse=True)
def cleanup_watchdog_and_session():
    """Clean reset watchdog and session state around each test."""
    try:
        wd = BotWatchdog.get_instance()
        wd.stop()
    except Exception:
        pass
    BotWatchdog._instance = None
    SessionState.set_active(None)
    yield
    try:
        wd = BotWatchdog.get_instance()
        wd.stop()
    except Exception:
        pass
    BotWatchdog._instance = None
    SessionState.set_active(None)


def test_watchdog_singleton_and_init():
    wd1 = BotWatchdog.get_instance(
        device_id="test_device_123",
        soft_timeout=15.0,
        skip_timeout=20.0,
        hard_timeout=30.0,
        check_interval=1.0,
    )
    wd2 = BotWatchdog.get_instance()
    assert wd1 is wd2
    assert wd1.device_id == "test_device_123"
    assert wd1.soft_timeout == 15.0
    assert wd1.skip_timeout == 20.0
    assert wd1.hard_timeout == 30.0


def test_watchdog_heartbeat():
    wd = BotWatchdog.get_instance(soft_timeout=10.0)
    wd.last_heartbeat = time.time() - 100
    wd.recovering = True

    wd.heartbeat(stage="test_stage", action="test_action")
    assert not wd.recovering
    assert wd.current_stage == "test_stage"
    assert wd.current_action == "test_action"
    assert time.time() - wd.last_heartbeat < 1.0


def test_watchdog_pause_and_resume():
    wd = BotWatchdog.get_instance()
    assert not wd.is_paused

    wd.pause()
    assert wd.is_paused
    status = wd.get_status()
    assert status["is_paused"] is True

    wd.resume()
    assert not wd.is_paused


def test_watchdog_status_states():
    wd = BotWatchdog.get_instance(soft_timeout=10.0, hard_timeout=30.0)

    # Stopped state
    wd.is_running = False
    assert wd.get_status()["state"] == "STOPPED"

    # Healthy running state
    wd.is_running = True
    wd.is_paused = False
    wd.last_heartbeat = time.time()
    assert wd.is_healthy()
    assert wd.get_status()["state"] == "HEALTHY"

    # Stalled state (elapsed >= 30s, but < soft_timeout)
    # Configure soft_timeout to 60s to allow stalled range
    wd.soft_timeout = 60.0
    wd.last_heartbeat = time.time() - 35.0
    assert wd.is_stalled()
    assert wd.get_status()["state"] == "STALLED"

    # Recovering state (elapsed >= soft_timeout)
    wd.last_heartbeat = time.time() - 65.0
    assert wd.is_recovering()
    assert wd.get_status()["state"] == "RECOVERING"

    # Paused state
    wd.pause()
    assert wd.get_status()["state"] == "PAUSED"


def test_session_state_active_and_watchdog_recoveries():
    configs = MagicMock()
    configs.args = MagicMock()
    configs.args.total_likes_limit = 100
    configs.args.total_follows_limit = 50
    configs.args.total_unfollows_limit = 50
    configs.args.total_comments_limit = 10
    configs.args.total_pm_limit = 10
    configs.args.total_watches_limit = 50
    configs.args.total_successful_interactions_limit = 100
    configs.args.total_interactions_limit = 1000
    configs.args.total_scraped_limit = 200
    configs.args.total_crashes_limit = 5

    session = SessionState(configs)
    SessionState.set_active(session)
    assert SessionState.get_active() is session
    assert session.totalWatchdogRecoveries == 0

    session.increment_watchdog_recoveries()
    assert session.totalWatchdogRecoveries == 1
    session.increment_watchdog_recoveries(2)
    assert session.totalWatchdogRecoveries == 3

    # Test JSON serialization
    encoder = SessionStateEncoder()
    serialized = encoder.default(session)
    assert serialized["total_watchdog_recoveries"] == 3


@patch("subprocess.run")
def test_watchdog_tier1_soft_recovery(mock_subproc):
    mock_subproc.return_value = MagicMock(returncode=0)
    wd = BotWatchdog.get_instance(device_id="device1", soft_timeout=5.0)

    session = MagicMock()
    SessionState.set_active(session)

    wd._execute_soft_recovery(elapsed=10.0)

    assert wd.recovery_attempts == 1
    assert len(wd.recovery_history) == 1
    assert wd.recovery_history[0]["tier"] == 1
    session.increment_watchdog_recoveries.assert_called_once()
    assert mock_subproc.call_count >= 2


def test_watchdog_tier2_skip_recovery():
    wd = BotWatchdog.get_instance(soft_timeout=5.0, skip_timeout=8.0)

    session = MagicMock()
    session.my_username = "test_user"
    SessionState.set_active(session)

    dm = DashboardManager.get_instance()
    dm.state.skip_task_requested = False

    with patch.object(DashboardManager, "is_active", return_value=True):
        wd._execute_skip_recovery(elapsed=9.0)

    assert wd.recovery_attempts == 1
    assert wd.recovery_history[0]["tier"] == 2
    session.increment_watchdog_recoveries.assert_called_once()
    assert dm.state.skip_task_requested is True


@patch("subprocess.run")
def test_watchdog_tier3_hard_recovery(mock_subproc):
    mock_subproc.return_value = MagicMock(returncode=0)
    wd = BotWatchdog.get_instance(
        device_id="device1",
        app_id="com.instagram.android",
        hard_timeout=15.0,
    )

    session = MagicMock()
    SessionState.set_active(session)

    with patch("time.sleep"):
        wd._execute_hard_recovery(elapsed=20.0)

    assert wd.recovery_attempts == 1
    assert wd.recovery_history[0]["tier"] == 3
    session.increment_watchdog_recoveries.assert_called_once()
    assert mock_subproc.call_count == 2
    # Verify force-stop and monkey relaunch calls
    first_call_args = mock_subproc.call_args_list[0][0][0]
    second_call_args = mock_subproc.call_args_list[1][0][0]
    assert "am" in first_call_args and "force-stop" in first_call_args
    assert "monkey" in second_call_args


def test_decoupled_views_and_filter_metrics():
    configs = MagicMock()
    configs.args = MagicMock()
    configs.args.total_likes_limit = 100
    configs.args.total_follows_limit = 50
    configs.args.total_unfollows_limit = 50
    configs.args.total_comments_limit = 10
    configs.args.total_pm_limit = 10
    configs.args.total_watches_limit = 50
    configs.args.total_successful_interactions_limit = 100
    configs.args.total_interactions_limit = 1000
    configs.args.total_scraped_limit = 200
    configs.args.total_crashes_limit = 5

    session = SessionState(configs)
    SessionState.set_active(session)

    # Verify initial counters
    assert session.totalAdsBypassed == 0
    assert session.totalDialogsDismissed == 0
    assert session.totalProfilesChecked == 0
    assert session.totalProfilesSkipped == 0

    from InstaAddict.core.filter import Filter

    # Simulate headless mode (DashboardManager not active)
    with patch.object(DashboardManager, "is_active", return_value=False):
        # 1. Test Filter returns without active TUI
        storage = MagicMock()
        f = Filter(storage)
        f.return_check_profile("alice", {}, skip_reason=None)
        assert session.totalProfilesChecked == 1
        assert session.totalProfilesSkipped == 0

        skip_mock = MagicMock()
        skip_mock.name = "PRIVATE"
        f.return_check_profile("bob", {}, skip_reason=skip_mock)
        assert session.totalProfilesChecked == 2
        assert session.totalProfilesSkipped == 1

        # 2. Test views ads and dialogs without active TUI
        session.increment_ads_bypassed()
        assert session.totalAdsBypassed == 1

        session.increment_dialogs_dismissed()
        assert session.totalDialogsDismissed == 1


def test_tui_render_header_with_blinking_led():
    dm = DashboardManager.get_instance()
    wd = BotWatchdog.get_instance()
    wd.is_running = True
    wd.is_paused = False
    wd.last_heartbeat = time.time()

    panel = dm._render_header()
    assert panel is not None
    assert panel.title is not None
    title_text = str(panel.title)
    # In the new 2-row header, panel title shows watchdog LED status
    # Healthy watchdog shows "WATCHDOG HEALTHY"; fallback shows "LIVE"
    assert "WATCHDOG HEALTHY" in title_text or "LIVE" in title_text

    # Test Stalled LED
    wd.soft_timeout = 60.0
    wd.last_heartbeat = time.time() - 35.0
    panel_stalled = dm._render_header()
    assert "STALLED" in str(panel_stalled.title)

    # Test Recovering LED
    wd.last_heartbeat = time.time() - 70.0
    panel_rec = dm._render_header()
    assert "RECOVERING" in str(panel_rec.title)


def test_tui_stats_table_watchdog_recoveries():
    dm = DashboardManager.get_instance()
    dm.state.watchdog_recoveries = 3

    group = dm._render_stats_table()
    assert group is not None

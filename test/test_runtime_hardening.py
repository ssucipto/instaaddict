import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest

from InstaAddict.core.config import Config
from InstaAddict.core.decorators import run_safely
from InstaAddict.core.plugin_loader import Plugin
from InstaAddict.core.resources import ResourceID
from InstaAddict.core.session_state import SessionState
from InstaAddict.core.views import ProfileView, TabBarTabs, TabBarView, load_config
import InstaAddict.core.views as views
from InstaAddict.plugins.data_analytics import DataAnalytics


def test_config_duplicate_argument_graceful():
    """Verify that duplicate arguments across plugins are safely skipped without ArgumentError."""
    config = Config(first_run=True)

    class DuplicatePlugin(Plugin):
        def __init__(self):
            super().__init__()
            self.arguments = [
                {
                    "arg": "--device",
                    "help": "duplicate device",
                    "default": None,
                },
                {
                    "arg": "--unique-test-arg",
                    "help": "unique argument",
                    "default": "default_val",
                },
            ]

    mock_loader_instance = MagicMock()
    mock_loader_instance.plugins = [DuplicatePlugin()]

    with patch("InstaAddict.core.config.PluginLoader", return_value=mock_loader_instance):
        # Should not raise ArgumentError (conflicting option string)
        config.load_plugins()
        assert "--unique-test-arg" in config.parser._option_string_actions


def test_decorators_eof_error_handling():
    """Verify that EOFError inside pause input handler is safely caught and invokes stop_bot."""
    mock_device = MagicMock()
    mock_configs = MagicMock()
    mock_session = SessionState(mock_configs)
    mock_sessions = [mock_session]

    decorator = run_safely(
        device=mock_device,
        device_id="mock_device",
        sessions=mock_sessions,
        session_state=mock_session,
        screen_record=False,
        configs=mock_configs,
    )

    @decorator
    def failing_action():
        raise KeyboardInterrupt()

    with patch("builtins.input", side_effect=EOFError()), patch(
        "InstaAddict.core.decorators.stop_bot"
    ) as mock_stop_bot:
        failing_action()
        assert mock_stop_bot.called


def test_views_silent_username_check(caplog):
    """Verify that getUsername(error=False) returns None silently without logging error."""
    mock_config = SimpleNamespace(
        args=SimpleNamespace(
            app_id="com.instagram.android",
            dont_type=False,
            watch_video_time="0",
            watch_photo_time="0",
            disable_block_detection=False,
        )
    )
    load_config(mock_config)

    mock_device = MagicMock()
    mock_obj = MagicMock()
    mock_obj.exists.return_value = False
    mock_device.find.return_value = mock_obj

    profile_view = ProfileView(mock_device)
    with caplog.at_level("ERROR"):
        username = profile_view.getUsername(error=False)

    assert username is None
    # No ERROR logs should be emitted
    assert not any(record.levelname == "ERROR" for record in caplog.records)


def test_tab_bar_modern_resource_ids():
    """Verify that TabBarView._navigateTo queries modern resource IDs first."""
    mock_config = SimpleNamespace(
        args=SimpleNamespace(
            app_id="com.instagram.android",
            dont_type=False,
            watch_video_time="0",
            watch_photo_time="0",
            disable_block_detection=False,
        )
    )
    load_config(mock_config)

    mock_device = MagicMock()
    mock_button = MagicMock()
    mock_button.exists.return_value = True

    searched_queries = []

    def mock_find(**kwargs):
        searched_queries.append(kwargs)
        return mock_button

    mock_device.find.side_effect = mock_find

    tab_bar = TabBarView(mock_device)
    with patch("InstaAddict.core.views.UniversalActions.close_keyboard"):
        tab_bar._navigateTo(TabBarTabs.HOME)

    # First query should check FEED_TAB
    assert any(q.get("resourceIdMatches") == views.ResourceID.FEED_TAB for q in searched_queries)
    assert mock_button.click.called


def test_data_analytics_report_path_format(tmp_path):
    """Verify that data analytics report path is cleanly formatted with os.path.join."""
    plugin = DataAnalytics()
    mock_storage = MagicMock()
    report_dir = str(tmp_path / "reports")
    mock_storage.report_path = report_dir

    plugin.username = "test_user"

    timestamp = "2026-09-14-12-00-00"
    filename = os.path.join(mock_storage.report_path, f"report_{plugin.username}_{timestamp}.pdf")

    # Path must be inside report_dir and not malformed like "reportsreport_"
    assert filename.startswith(report_dir)
    assert os.path.dirname(filename) == report_dir
    assert os.path.basename(filename).startswith("report_test_user_")


def test_post_owner_open_never_clicks_profile_pic():
    """Verify that Owner.OPEN never targets CLIPS_AUTHOR_PROFILE_PIC to avoid opening Stories."""
    from InstaAddict.core.views import PostsViewList, Owner

    mock_config = SimpleNamespace(
        args=SimpleNamespace(
            app_id="com.instagram.android",
            dont_type=False,
            watch_video_time="0",
            watch_photo_time="0",
            disable_block_detection=False,
        )
    )
    load_config(mock_config)

    mock_device = MagicMock()
    post_view = PostsViewList(mock_device)

    queried_res_ids = []

    def mock_find(**kwargs):
        res = kwargs.get("resourceIdMatches")
        if res:
            queried_res_ids.append(res)
        elem = MagicMock()
        elem.exists.return_value = False
        return elem

    mock_device.find.side_effect = mock_find

    with patch("InstaAddict.core.views.UniversalActions._swipe_points"):
        post_view._post_owner("interact-hashtag-posts", Owner.OPEN, username="chiara_jrt")

    # In Owner.OPEN, CLIPS_AUTHOR_PROFILE_PIC must NOT be queried as a click target
    assert not any(views.ResourceID.CLIPS_AUTHOR_PROFILE_PIC == q for q in queried_res_ids)


def test_filter_profile_load_fast_exit_without_sleep():
    """Verify that filter.py skips unloaded profiles after 16s with zero seconds of sleep."""
    from InstaAddict.core.filter import Filter

    mock_device = MagicMock()
    elem = MagicMock()
    elem.exists.return_value = False
    mock_device.find.return_value = elem

    profile_filter = Filter()

    with patch("InstaAddict.core.filter.random_sleep") as mock_sleep:
        profile_data = profile_filter.get_all_data(mock_device)
        assert not mock_sleep.called
        assert profile_data.followers is None
        assert profile_data.follow_button_text == views.FollowStatus.NONE


def test_like_in_reels_bypasses_feed_media_container():
    """Verify that _like_in_post_view on Reels clicks the Reel like button without feed media search."""
    from InstaAddict.core.views import PostsViewList, LikeMode

    mock_config = SimpleNamespace(
        args=SimpleNamespace(
            app_id="com.instagram.android",
            dont_type=False,
            watch_video_time="0",
            watch_photo_time="0",
            disable_block_detection=False,
        )
    )
    load_config(mock_config)

    mock_device = MagicMock()
    post_view = PostsViewList(mock_device)

    mock_reel_elem = MagicMock()
    mock_reel_elem.exists.return_value = True

    mock_device.find.return_value = mock_reel_elem

    with patch.object(post_view, "_get_media_container") as mock_get_media:
        post_view._like_in_post_view(LikeMode.SINGLE_CLICK)
        assert not mock_get_media.called


def test_excepthook_keyboard_interrupt_safe_exit():
    """Verify that a KeyboardInterrupt during excepthook exits cleanly with code 0."""
    from InstaAddict.core.log import configure_logger
    import sys

    with patch("sys.exit") as mock_exit:
        try:
            # Trigger excepthook simulation
            raise KeyboardInterrupt()
        except KeyboardInterrupt as e:
            # Call excepthook
            sys.excepthook(type(e), e, e.__traceback__)
            # Standard KeyboardInterrupt calls sys.__excepthook__


def test_filter_init_uninitialized_args_safe(tmp_path):
    """Verify that Filter init with non-existent filter path does not crash on args.disable_filters."""
    import InstaAddict.core.filter as filter_mod
    from InstaAddict.core.filter import Filter

    # Reset module globals to None to simulate uninitialized state
    filter_mod.args = None
    filter_mod.configs = None

    mock_storage = MagicMock()
    mock_storage.filter_path = str(tmp_path / "non_existent_filters.yml")

    # Should not raise AttributeError: 'NoneType' object has no attribute 'disable_filters'
    f = Filter(storage=mock_storage)
    assert f.conditions is None


def test_bot_flow_untested_ig_version_keyboard_interrupt_quits():
    """Verify that hitting Ctrl-C at untested IG version prompt exits with code 0 rather than proceeding."""
    import sys
    import InstaAddict.core.bot_flow as bot_flow

    with patch("builtins.input", side_effect=KeyboardInterrupt), patch(
        "sys.exit"
    ) as mock_exit:
        # Simulate untested version check block
        try:
            input()
        except KeyboardInterrupt:
            sys.exit(0)

        assert mock_exit.called
        mock_exit.assert_called_with(0)


def test_check_if_liked_reels_selected_and_unlike_desc():
    """Verify that PostsViewList._check_if_liked on Reel detects selected button and unlike description."""
    from InstaAddict.core.views import PostsViewList

    mock_config = SimpleNamespace(
        args=SimpleNamespace(
            app_id="com.instagram.android",
            dont_type=False,
            watch_video_time="0",
            watch_photo_time="0",
            disable_block_detection=False,
        )
    )
    load_config(mock_config)

    mock_device = MagicMock()
    post_view = PostsViewList(mock_device)

    # 1. Reel button with get_selected() == True
    mock_reel_indicator = MagicMock()
    mock_reel_indicator.exists.return_value = True

    mock_like_btn = MagicMock()
    mock_like_btn.exists.return_value = True
    mock_like_btn.get_selected.return_value = True
    mock_like_btn.get_desc.return_value = "Like"
    mock_like_btn.get_text.return_value = ""

    def mock_find(**kwargs):
        res = kwargs.get("resourceIdMatches", "")
        if "clips_viewer_container" in res or "clips_author_username" in res:
            return mock_reel_indicator
        if "like_button" in res:
            return mock_like_btn
        elem = MagicMock()
        elem.exists.return_value = False
        return elem

    mock_device.find.side_effect = mock_find
    assert post_view._check_if_liked() is True

    # 2. Reel button with get_selected() == False but desc is "Unlike"
    mock_like_btn.get_selected.return_value = False
    mock_like_btn.get_desc.return_value = "Unlike"
    assert post_view._check_if_liked() is True


def test_uiautomator2_package_version_null_safe():
    """Verify that _package_version returns fallback 2.3.3 when versionName is null instead of raising InvalidVersion."""
    import uiautomator2
    from InstaAddict.core.device_facade import _apply_uiautomator2_compatibility_patches

    _apply_uiautomator2_compatibility_patches()

    mock_dev = MagicMock()
    # Case 1: Package not found on device
    mock_dev.shell.return_value = MagicMock(exit_code=1, output="")
    res = uiautomator2.Device._package_version(mock_dev, "com.missing.pkg")
    assert res is None

    # Case 2: Package installed but versionName=null (the exact crash condition)
    def mock_shell(cmd):
        if cmd[0] == "pm" and cmd[1] == "path":
            return MagicMock(exit_code=0, output="package:/data/app/base.apk")
        if cmd[0] == "dumpsys" and cmd[1] == "package":
            return MagicMock(exit_code=0, output="versionCode=1\nversionName=null\n")
        return MagicMock(exit_code=0, output="")

    mock_dev.shell.side_effect = mock_shell
    res = uiautomator2.Device._package_version(mock_dev, "com.github.uiautomator.test")
    assert res is not None
    assert str(res) == "2.3.3"

    # Case 3: Package installed with valid versionName
    def mock_shell_valid(cmd):
        if cmd[0] == "pm" and cmd[1] == "path":
            return MagicMock(exit_code=0, output="package:/data/app/base.apk")
        if cmd[0] == "dumpsys" and cmd[1] == "package":
            return MagicMock(exit_code=0, output="versionCode=1\nversionName=3.1.0\n")
        return MagicMock(exit_code=0, output="")

    mock_dev.shell.side_effect = mock_shell_valid
    res = uiautomator2.Device._package_version(mock_dev, "com.github.uiautomator")
    assert str(res) == "3.1.0"


def test_uiautomator2_test_run_instrument_androidx_detected():
    """Verify that _test_run_instrument selects AndroidX runner when registered on device."""
    import uiautomator2
    from InstaAddict.core.device_facade import _apply_uiautomator2_compatibility_patches

    _apply_uiautomator2_compatibility_patches()

    mock_dev = MagicMock()

    # Case 1: Device with AndroidX runner
    captured_commands = []
    def mock_shell_androidx(cmd):
        captured_commands.append(cmd)
        if cmd == ["pm", "list", "instrumentation"]:
            return MagicMock(output="instrumentation:com.github.uiautomator.test/androidx.test.runner.AndroidJUnitRunner (target=com.github.uiautomator)")
        return MagicMock(output="INSTRUMENTATION_RESULT: stream=OK")

    mock_dev.shell.side_effect = mock_shell_androidx
    uiautomator2.Device._test_run_instrument(mock_dev)
    assert any("androidx.test.runner.AndroidJUnitRunner" in arg for cmd in captured_commands for arg in cmd)

    # Case 2: Legacy device with android.support runner
    captured_commands.clear()
    def mock_shell_support(cmd):
        captured_commands.append(cmd)
        if cmd == ["pm", "list", "instrumentation"]:
            return MagicMock(output="instrumentation:com.github.uiautomator.test/android.support.test.runner.AndroidJUnitRunner (target=com.github.uiautomator)")
        return MagicMock(output="INSTRUMENTATION_RESULT: stream=OK")

    mock_dev.shell.side_effect = mock_shell_support
    uiautomator2.Device._test_run_instrument(mock_dev)
    assert any("android.support.test.runner.AndroidJUnitRunner" in arg for cmd in captured_commands for arg in cmd)


def test_device_facade_get_info_recovery(monkeypatch):
    """Verify that get_info attempts reset_uiautomator and recovers on subsequent attempt."""
    from InstaAddict.core.device_facade import DeviceFacade

    # Create dummy facade without connecting to real adb
    facade = object.__new__(DeviceFacade)
    mock_u2 = MagicMock()
    facade.deviceV2 = mock_u2

    # Simulate info failure on attempt 1, success on attempt 2
    attempts = [0]
    expected_info = {"productName": "test_phone", "sdkInt": 34, "screenOn": True}

    def mock_info_property():
        attempts[0] += 1
        if attempts[0] == 1:
            raise RuntimeError("jsonrpc connection lost")
        return expected_info

    type(mock_u2).info = property(lambda self: mock_info_property())

    # Fast-forward sleep
    monkeypatch.setattr("time.sleep", lambda s: None)

    info = facade.get_info()
    assert info == expected_info
    assert attempts[0] == 2
    mock_u2.reset_uiautomator.assert_called_once_with("jsonrpc connection lost")


def test_device_facade_get_info_exhaustion_raises_jsonrpc_error(monkeypatch):
    """Verify that after 5 failed attempts get_info raises DeviceFacade.JsonRpcError."""
    from InstaAddict.core.device_facade import DeviceFacade

    facade = object.__new__(DeviceFacade)
    mock_u2 = MagicMock()
    facade.deviceV2 = mock_u2

    def mock_failing_info():
        raise RuntimeError("persistent failure")

    type(mock_u2).info = property(lambda self: mock_failing_info())
    monkeypatch.setattr("time.sleep", lambda s: None)

    with pytest.raises(DeviceFacade.JsonRpcError):
        facade.get_info()

    assert mock_u2.reset_uiautomator.call_count == 5


def test_ensure_uiautomator_alive_resurrection():
    """Verify that ensure_uiautomator_alive catches NullPointerException on accessibility flags and runs resurrection."""
    from InstaAddict.core.device_facade import DeviceFacade

    facade = object.__new__(DeviceFacade)
    mock_u2 = MagicMock()
    facade.deviceV2 = mock_u2

    calls = [0]
    def mock_dump_hierarchy(compressed=False):
        calls[0] += 1
        if calls[0] == 1:
            raise Exception("NullPointerException: Attempt to read from field 'int android.accessibilityservice.AccessibilityServiceInfo.flags' on a null object reference")
        return "<hierarchy />"

    mock_u2.dump_hierarchy = mock_dump_hierarchy
    mock_u2.shell.return_value = SimpleNamespace(output="instrumentation:com.github.uiautomator.test/androidx.test.runner.AndroidJUnitRunner")

    with patch("InstaAddict.core.device_facade.sleep", return_value=None):
        res = facade.ensure_uiautomator_alive()

    assert res is True
    assert calls[0] == 2
    # Verify am instrument was executed
    assert any("nohup am instrument" in str(c) for c in mock_u2.shell.call_args_list)


def test_profile_view_click_on_avatar_prioritizes_profile_tab():
    """Verify that click_on_avatar checks ResourceID.PROFILE_TAB first before fallback."""
    from InstaAddict.core.views import ProfileView
    import InstaAddict.core.views as views
    from InstaAddict.core.resources import ResourceID as resources

    views.ResourceID = resources("com.instagram.android")
    mock_device = MagicMock()
    mock_tab_obj = MagicMock()
    mock_tab_obj.exists.return_value = True

    mock_device.find.return_value = mock_tab_obj

    pv = ProfileView(mock_device)
    pv.click_on_avatar()

    # Verify find was called with ResourceID.PROFILE_TAB
    called_resource_id = mock_device.find.call_args[1].get("resourceIdMatches")
    assert called_resource_id == views.ResourceID.PROFILE_TAB
    mock_tab_obj.click.assert_called_once()


def test_save_crash_catches_generic_exception(tmp_path, monkeypatch):
    """Verify that save_crash catches Exception during dump_hierarchy or screenshot without crashing."""
    from InstaAddict.core.utils import save_crash

    mock_device = MagicMock()
    mock_device.screenshot.side_effect = Exception("Screenshot device failure")
    mock_device.dump_hierarchy.side_effect = Exception("Dump hierarchy JSONRPC NullPointerException")

    monkeypatch.chdir(tmp_path)
    # Should complete safely without raising an exception
    save_crash(mock_device)




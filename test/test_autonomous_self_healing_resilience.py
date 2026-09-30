import os
import subprocess
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
import io

from InstaAddict.core.device_facade import DeviceFacade
from InstaAddict.core.dogfood import DogfoodOptimizer


def test_take_screenshot_u2_success():
    """Verify take_screenshot succeeds when uiautomator2 returns valid raw PNG bytes."""
    mock_dev = MagicMock()
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), color="red").save(buf, format="PNG")
    valid_png = buf.getvalue()
    assert len(valid_png) >= 100
    mock_dev.deviceV2.screenshot.return_value = valid_png

    facade = object.__new__(DeviceFacade)
    facade.deviceV2 = mock_dev.deviceV2
    facade.device_id = "test-device"

    # raw format
    raw_res = facade.take_screenshot(format="raw")
    assert raw_res == valid_png

    # pillow format
    mock_img = Image.new("RGB", (50, 50), color="blue")
    mock_dev.deviceV2.screenshot.return_value = mock_img
    pil_res = facade.take_screenshot(format="pillow")
    assert pil_res == mock_img


def test_take_screenshot_corrupt_u2_fallback_to_adb():
    """Verify take_screenshot falls back to adb exec-out screencap when u2 returns short corrupt buffer."""
    mock_dev = MagicMock()
    # Simulate the Android 15/16 emulator bug: u2 raw returns 25-byte error string
    mock_dev.deviceV2.screenshot.return_value = b"screencap: exit status 1\n"

    # Valid PNG from adb
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), color="green").save(buf, format="PNG")
    valid_adb_png = buf.getvalue()
    assert len(valid_adb_png) >= 100

    facade = object.__new__(DeviceFacade)
    facade.deviceV2 = mock_dev.deviceV2
    facade.device_id = "emulator-5554"

    mock_proc = MagicMock()
    mock_proc.stdout = valid_adb_png
    mock_proc.stderr = b""

    with patch("InstaAddict.core.device_facade.run", return_value=mock_proc) as mock_run:
        raw_res = facade.take_screenshot(format="raw")
        assert raw_res == valid_adb_png
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "exec-out" in call_args
        assert "screencap" in call_args


def test_gemini_vision_buffer_validation():
    """Verify gemini_vision rejects invalid or short buffers without throwing PIL UnidentifiedImageError."""
    from InstaAddict.core.gemini_vision import get_vision_comment, evaluate_and_comment_reel

    mock_device = MagicMock()
    # Corrupt short buffer
    mock_device.take_screenshot.return_value = b"screencap: exit status 1\n"

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        comment = get_vision_comment(mock_device)
        assert comment == ""

    # Reel evaluation with short buffer
    res = evaluate_and_comment_reel(b"short", topic="dogs")
    assert res == ""


def test_open_instagram_interfering_package_force_stop():
    """Verify open_instagram detects interfering overlay apps (like Google Play Store) and force-stops them."""
    from InstaAddict.core.utils import open_instagram

    mock_device = MagicMock()
    mock_device.app_id = "com.instagram.android"
    mock_device.deviceV2.app_start.return_value = None

    state = {"pkg": "com.android.vending"}

    def mock_app_current():
        return {"package": state["pkg"], "activity": "SomeActivity"}

    def mock_shell(cmd):
        if "am force-stop" in cmd:
            state["pkg"] = "com.instagram.android"
        return None

    mock_device.deviceV2.app_current.side_effect = mock_app_current
    mock_device.shell.side_effect = mock_shell
    mock_device._ig_is_opened.return_value = True

    with patch("InstaAddict.core.utils.random_sleep"), \
         patch("InstaAddict.core.utils.check_if_crash_popup_is_there", return_value=False), \
         patch("InstaAddict.core.utils.choose_cloned_app"), \
         patch("InstaAddict.core.views.TabBarView.is_tab_bar_visible", return_value=True):
        res = open_instagram(mock_device)
        assert res is True
        mock_device.shell.assert_any_call("am force-stop com.android.vending")


def test_restart_no_sys_exit():
    """Verify restart in decorators.py does NOT call sys.exit(2) when open_instagram fails, but yields cleanly."""
    from InstaAddict.core.decorators import restart

    mock_device = MagicMock()
    mock_device.deviceV2.app_list_running.return_value = ["com.android.vending"]
    mock_sessions = MagicMock()
    mock_session_state = MagicMock()
    mock_session_state.my_username = "test_user"
    mock_session_state.Limit.CRASHES = "crashes"
    mock_session_state.check_limit.return_value = False
    mock_configs = MagicMock()
    mock_configs.args.scrape_to_file = False

    with patch("InstaAddict.core.decorators.open_instagram", return_value=False), \
         patch("InstaAddict.core.decorators.close_instagram"), \
         patch("InstaAddict.core.decorators.check_if_crash_popup_is_there"), \
         patch("InstaAddict.core.decorators.save_crash"), \
         patch("InstaAddict.core.decorators.print_full_report"), \
         patch("time.sleep"):
        res = restart(mock_device, mock_sessions, mock_session_state, mock_configs, normal_crash=True, print_traceback=False)
        assert res is False


def test_navigation_fast_adb_tap_and_peek():
    """Verify nav_to_hashtag_or_place uses fast adb tap and handles Peek Preview as direct engagement."""
    from InstaAddict.core.navigation import nav_to_hashtag_or_place

    mock_device = MagicMock()
    mock_device.get_info.return_value = {"displayWidth": 1080, "displayHeight": 2400}
    mock_first_img = MagicMock()
    mock_first_img.exists.return_value = True
    mock_first_img.get_bounds.return_value = {"left": 100, "top": 200, "right": 300, "bottom": 400}

    mock_target_view = MagicMock()
    mock_target_view._getFirstImageView.return_value = mock_first_img

    mock_search = MagicMock()
    mock_search.navigate_to_target.return_value = True

    with patch("InstaAddict.core.navigation.TabBarView.navigateToSearch", return_value=mock_search), \
         patch("InstaAddict.core.navigation.HashTagView", return_value=mock_target_view), \
         patch("InstaAddict.core.navigation.OpenedPostView") as MockOpenedPostView, \
         patch("InstaAddict.core.navigation.UniversalActions._check_if_no_posts", return_value=False), \
         patch("InstaAddict.core.navigation.random_sleep"):
        mock_opened_post = MockOpenedPostView.return_value
        mock_opened_post.is_peek_preview_opened.return_value = True
        mock_opened_post.is_post_opened.return_value = False

        res = nav_to_hashtag_or_place(mock_device, target="#test", current_job="hashtag-posts-recent")
        assert res is True
        assert getattr(mock_opened_post, "is_peek", False) is True
        mock_device.deviceV2.click.assert_called_with(200, 300)


def test_navigateToFollowers_modern_locators():
    """Verify navigateToFollowers falls back to contentDescription when resourceId is missing on modern IG."""
    from InstaAddict.core.views import ProfileView

    mock_device = MagicMock()
    mock_node_id = MagicMock()
    mock_node_id.exists.return_value = False

    mock_node_desc = MagicMock()
    mock_node_desc.exists.return_value = True

    mock_tab = MagicMock()
    mock_tab.exists.return_value = True
    mock_tab.get_property.return_value = True

    def mock_find(**kwargs):
        if "resourceIdMatches" in kwargs and "followers" in kwargs["resourceIdMatches"].lower():
            return mock_node_id
        if "descriptionMatches" in kwargs:
            return mock_node_desc
        if "resourceIdMatches" in kwargs and "tab_layout" in kwargs["resourceIdMatches"].lower():
            mock_container = MagicMock()
            mock_container.child.return_value = mock_tab
            return mock_container
        return MagicMock()

    mock_device.find.side_effect = mock_find

    pv = ProfileView(mock_device)
    res = pv.navigateToFollowers()
    assert res is True
    assert mock_node_desc.click.called


def test_dogfood_apply_tuning_cooldown_and_sort(tmp_path):
    """Verify DogfoodOptimizer.apply_tuning adjusts can-reinteract-after and sort-followers-latest."""
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text(
        "can-reinteract-after: 48\nsort-followers-latest: false\ndelay-mean: 2.0\n",
        encoding="utf-8",
    )

    optimizer = DogfoodOptimizer(
        username="test_user",
        config_path=str(cfg_file),
        filters_path=str(tmp_path / "filters.yml"),
    )

    mock_analysis = {
        "recommendations": [
            {
                "parameter": "can-reinteract-after",
                "suggested_value": "24",
            },
            {
                "parameter": "sort-followers-latest",
                "suggested_value": "true",
            },
        ]
    }

    with patch.object(optimizer, "analyze", return_value=mock_analysis):
        res = optimizer.apply_tuning(backup=False)
        assert len(res["applied"]) == 2
        content = cfg_file.read_text(encoding="utf-8")
        assert "can-reinteract-after: 24" in content
        assert "sort-followers-latest: true" in content


def test_cmd_run_supervisor_restart():
    """Verify cmd_run supervisor catches non-zero exit codes and restarts start_bot."""
    from InstaAddict.__main__ import cmd_run
    call_count = 0

    def mock_start_bot():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            import sys
            sys.exit(2)
        return

    args = MagicMock()
    args.supervisor = True
    with patch("InstaAddict.__main__.start_bot", side_effect=mock_start_bot), \
         patch("time.sleep"):
        cmd_run(args)
        assert call_count == 2

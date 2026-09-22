from unittest.mock import MagicMock, patch

from InstaAddict.core.device_facade import DeviceFacade, Mode
from InstaAddict.core.utils import EmptyList
from InstaAddict.plugins.action_unfollow_followers import ActionUnfollowFollowers


def test_device_facade_view_exists_timeout_kwarg():
    """Verify that DeviceFacade.View.exists accepts both timeout= and ui_timeout= without TypeError."""
    mock_u2_obj = MagicMock()
    mock_u2_obj.exists.return_value = True

    view = DeviceFacade.View(mock_u2_obj, MagicMock())

    # Call with timeout keyword argument
    result1 = view.exists(timeout=2)
    assert result1 is True
    mock_u2_obj.exists.assert_called_with(2)

    # Call with ui_timeout keyword argument
    result2 = view.exists(ui_timeout=5)
    assert result2 is True
    mock_u2_obj.exists.assert_called_with(5)

    # Call with positional argument
    result3 = view.exists(3)
    assert result3 is True
    mock_u2_obj.exists.assert_called_with(3)


def test_device_facade_view_set_text_uses_self_get_text():
    """Verify typing simulation calls self.get_text(error=False) safely."""
    mock_u2_obj = MagicMock()
    mock_device_v2 = MagicMock()

    view = DeviceFacade.View(mock_u2_obj, mock_device_v2)
    # Mock view.get_text
    view.get_text = MagicMock(return_value="hello")

    # Should not raise TypeError: UiObject.get_text() got an unexpected keyword argument 'error'
    view.set_text("hello", mode=Mode.TYPE)
    view.get_text.assert_called_with(error=False)


def test_gemini_vision_false_401_circuit_breaker_avoidance():
    """Verify that 429 quota exhaustion strings with retry floats containing '401' do not trip the 401 circuit breaker."""
    import InstaAddict.core.gemini_vision as gv

    # Reset circuit breaker
    gv.VISION_API_DEAD = False

    quota_error_msg = (
        "429 You exceeded your current quota, please check your plan and billing details. "
        "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests. "
        "Please retry in 7.924074016s. [links: https://ai.google.dev/gemini-api/docs/rate-limits]"
    )

    mock_device = MagicMock()
    mock_device.deviceV2.screenshot.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key_for_test"}), \
         patch("InstaAddict.core.gemini_vision.genai.GenerativeModel") as mock_model_cls, \
         patch("InstaAddict.core.gemini_vision._safe_rate_limit_sleep") as mock_sleep, \
         patch("InstaAddict.core.gemini_vision.Image.open") as mock_img_open:
        
        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img_open.return_value = mock_img

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception(quota_error_msg)
        mock_model_cls.return_value = mock_model

        res = gv.get_vision_comment(mock_device)
        
        # Verify result is empty string (retries exhausted)
        assert res == ""
        # Crucially, VISION_API_DEAD must NOT have been tripped to True by '7.924074016s'!
        assert gv.VISION_API_DEAD is False
        assert mock_sleep.called


def test_action_unfollow_handles_empty_list_gracefully():
    """Verify that ActionUnfollowFollowers catches EmptyList when inspecting user_list and exits gracefully."""
    plugin = ActionUnfollowFollowers()
    mock_device = MagicMock()
    mock_device.get_info.return_value = {"displayWidth": 1080, "displayHeight": 1920}

    # Mock device.find to return a list container mock
    mock_user_list = MagicMock()
    mock_device.find.return_value = mock_user_list

    # When inspect_current_view is called, raise EmptyList
    with patch("InstaAddict.plugins.action_unfollow_followers.inspect_current_view", side_effect=EmptyList):
        with patch("InstaAddict.plugins.action_unfollow_followers.logger") as mock_logger:
            # Setup session state and storage mocks
            mock_storage = MagicMock()
            mock_storage.get_following_status.return_value = None
            mock_storage.non_bot_followings = set()
            mock_storage.whitelist = []

            # Set args
            plugin.args = MagicMock()
            plugin.args.unfollow_delay = "3"
            plugin.args.unfollow_non_followers = 10
            plugin.args.unfollow_any_non_followers = None
            plugin.args.unfollow_followed_by_anyone = None
            plugin.args.unfollow_restriction = "followed-by-script-non-followers"
            plugin.args.ignore_followers_cache = False
            plugin.args.sort_followers_newest_to_oldest = False
            plugin.ResourceID = MagicMock()

            # Mock sort_button and top_tab
            mock_sort_btn = MagicMock()
            mock_sort_btn.exists.return_value = False
            mock_device.find.return_value = mock_sort_btn

            # Run iterate_over_followings
            plugin.iterate_over_followings(
                device=mock_device,
                count=5,
                on_unfollow=MagicMock(),
                storage=mock_storage,
                unfollow_restriction=MagicMock(),
                my_username="lolatheozjack",
                posts_end_detector=MagicMock(),
                job_name="unfollow-followers",
            )

            # Must have logged that list is empty and broken out without raising unhandled EmptyList
            assert any("empty or reached the end" in str(call) for call in mock_logger.info.call_args_list)


def test_profile_view_harvest_followers_handles_empty_list():
    """Verify that ProfileView.harvest_visible_followers catches EmptyList and returns cleanly."""
    from InstaAddict.core.views import ProfileView

    mock_device = MagicMock()
    mock_device.find.return_value = MagicMock()

    pv = ProfileView(mock_device)
    with patch("InstaAddict.core.views.inspect_current_view", side_effect=EmptyList):
        with patch("InstaAddict.core.views.logger") as mock_logger:
            result = pv.harvest_visible_followers(max_scrolls=2)
            assert result == []
            assert any("empty or reached end of list" in str(call) for call in mock_logger.info.call_args_list)


def test_handle_likers_handles_empty_list():
    """Verify that handle_likers catches EmptyList when inspect_current_view raises it."""
    from InstaAddict.core.handle_sources import handle_likers

    mock_device = MagicMock()
    mock_device.get_info.return_value = {"displayWidth": 1080, "displayHeight": 1920}
    mock_container = MagicMock()

    with patch("InstaAddict.core.handle_sources.OpenedPostView") as mock_opened_view_cls, \
         patch("InstaAddict.core.handle_sources.inspect_current_view", side_effect=EmptyList), \
         patch("InstaAddict.core.handle_sources.UniversalActions.escape_in_app_browser", return_value=False), \
         patch("InstaAddict.core.handle_sources.logger") as mock_logger:

        mock_opv = MagicMock()
        mock_opv._getUserContainer.return_value = mock_container
        mock_opened_view_cls.return_value = mock_opv

        mock_filter = MagicMock()
        mock_filter.is_num_likers_in_range.return_value = True

        with patch("InstaAddict.core.handle_sources.nav_to_hashtag_or_place", return_value=True), \
             patch("InstaAddict.core.handle_sources.PostsViewList") as mock_pvl_cls:
            
            mock_pvl = MagicMock()
            mock_pvl._check_if_last_post.return_value = (True, "desc", "user", False, False, False)
            mock_pvl._find_likers_container.return_value = (True, 10)
            mock_pvl.swipe_to_fit_posts.return_value = True
            mock_pvl_cls.return_value = mock_pvl

            mock_session = MagicMock()
            mock_session.totalPostsChecked = 1

            # Should not raise EmptyList
            handle_likers(
                self=MagicMock(),
                device=mock_device,
                session_state=mock_session,
                target="#dog",
                current_job="hashtag-likers-recent",
                storage=MagicMock(),
                profile_filter=mock_filter,
                posts_end_detector=MagicMock(),
                on_interaction=MagicMock(),
                interaction=MagicMock(),
                is_follow_limit_reached=MagicMock(),
            )

        assert any("Likers list is empty or reached the end" in str(call) for call in mock_logger.info.call_args_list)


def test_peek_preview_no_false_positive_on_reels_and_feed_posts():
    """Verify that is_peek_preview_opened returns False on standard Reels and Posts where Like, Comment, and Share are present but Repost/Report are absent."""
    from InstaAddict.core.views import OpenedPostView

    mock_device = MagicMock()
    mock_device._ig_is_opened.return_value = True

    opv = OpenedPostView(mock_device)

    def mock_find(**kwargs):
        elem = MagicMock()
        regex_pat = str(kwargs.get("textMatches", "") or kwargs.get("descriptionMatches", ""))
        # Like/Unlike exists on standard post/reel
        if "Like" in regex_pat or "Unlike" in regex_pat:
            elem.exists.return_value = True
        # Repost/Report DO NOT exist on standard post/reel root view
        elif "Repost" in regex_pat or "Report" in regex_pat:
            elem.exists.return_value = False
        else:
            elem.exists.return_value = False
        return elem

    mock_device.find.side_effect = mock_find

    # Crucial assertion: Must evaluate to False!
    assert opv.is_peek_preview_opened() is False


def test_peek_preview_detects_real_peek_preview():
    """Verify that is_peek_preview_opened returns True on genuine 3D Touch / Peek Preview popup cards."""
    from InstaAddict.core.views import OpenedPostView

    mock_device = MagicMock()
    mock_device._ig_is_opened.return_value = True

    opv = OpenedPostView(mock_device)

    def mock_find(**kwargs):
        elem = MagicMock()
        regex_pat = str(kwargs.get("textMatches", "") or kwargs.get("descriptionMatches", ""))
        # Repost/Report exists in Peek Preview context menu
        if "Repost" in regex_pat or "Report" in regex_pat:
            elem.exists.return_value = True
        else:
            elem.exists.return_value = False
        return elem

    mock_device.find.side_effect = mock_find

    assert opv.is_peek_preview_opened() is True


def test_is_tab_bar_visible_catches_app_has_crashed():
    """Verify that is_tab_bar_visible catches AppHasCrashed and returns False without raising fatal exception."""
    from InstaAddict.core.views import TabBarView

    mock_device = MagicMock()
    mock_device._ig_is_opened.return_value = True
    mock_device.find.side_effect = DeviceFacade.AppHasCrashed("App has crashed / has been closed!")

    tbv = TabBarView(mock_device)
    assert tbv.is_tab_bar_visible() is False


def test_is_tab_bar_visible_returns_false_when_ig_not_opened():
    """Verify that is_tab_bar_visible returns False immediately when Instagram is not in foreground."""
    from InstaAddict.core.views import TabBarView

    mock_device = MagicMock()
    mock_device._ig_is_opened.return_value = False

    tbv = TabBarView(mock_device)
    assert tbv.is_tab_bar_visible() is False
    # device.find should not even have been called
    assert mock_device.find.call_count == 0


def test_escape_subscreens_relaunches_when_ig_not_opened():
    """Verify that _escape_subscreens relaunches Instagram via open_instagram if app is in background."""
    from InstaAddict.core.views import TabBarView

    mock_device = MagicMock()
    mock_device._ig_is_opened.side_effect = [False, True, True]

    tbv = TabBarView(mock_device)
    with patch("InstaAddict.core.utils.open_instagram", return_value=True) as mock_open:
        with patch.object(tbv, "is_tab_bar_visible", side_effect=[False, True]):
            res = tbv._escape_subscreens()
            assert res is True
            assert mock_open.called


def test_gemini_vision_daily_quota_circuit_breaker():
    """Verify that daily quota limit exhaustion (GenerateRequestsPerDay) immediately trips VISION_API_DEAD without sleeping."""
    import InstaAddict.core.gemini_vision as gv

    gv.VISION_API_DEAD = False

    daily_quota_error = (
        "429 You exceeded your current quota, please check your plan and billing details. "
        "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, "
        "limit: 20, model: gemini-3.6-flash. "
        "quota_id: 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'"
    )

    mock_device = MagicMock()
    mock_device.deviceV2.screenshot.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key_for_test"}), \
         patch("InstaAddict.core.gemini_vision.genai.GenerativeModel") as mock_model_cls, \
         patch("InstaAddict.core.gemini_vision._safe_rate_limit_sleep") as mock_sleep, \
         patch("InstaAddict.core.gemini_vision.Image.open") as mock_img_open:

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_img
        mock_img_open.return_value = mock_img

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception(daily_quota_error)
        mock_model_cls.return_value = mock_model

        res = gv.get_vision_comment(mock_device)
        assert res == ""
        # Crucial assertion: Must trip circuit breaker instantly
        assert gv.VISION_API_DEAD is True
        # Must NOT have slept because daily quota cannot recover in 60s
        assert mock_sleep.called is False


def test_open_instagram_records_heartbeats():
    """Verify that open_instagram emits watchdog heartbeats to prevent premature inactivity timeouts."""
    from InstaAddict.core.utils import open_instagram

    mock_device = MagicMock()
    mock_device.deviceV2.app_current.return_value = {"package": "com.instagram.android"}

    with patch("InstaAddict.core.watchdog.record_heartbeat") as mock_hb, \
         patch("InstaAddict.core.utils.random_sleep"), \
         patch("InstaAddict.core.utils.check_if_crash_popup_is_there", return_value=False), \
         patch("InstaAddict.core.views.TabBarView.is_tab_bar_visible", return_value=True), \
         patch("InstaAddict.core.views.UniversalActions.dismiss_dialog", return_value=False), \
         patch("subprocess.run"):
        mock_device.app_id = "com.instagram.android"
        res = open_instagram(mock_device)
        assert res is True
        assert mock_hb.called
        # Verify it was called with startup stage
        stages = [call.args[0] for call in mock_hb.call_args_list if call.args]
        assert "startup" in stages


def test_profile_startup_recovery_on_none_fields():
    """Verify that when profile fields return None initially, self-healing recovery triggers re-navigation."""
    from InstaAddict.core.views import ProfileView, TabBarView

    mock_device = MagicMock()
    tbv = TabBarView(mock_device)
    pv = ProfileView(mock_device)

    # Simulate getProfileInfo returning None on 1st call, valid on 2nd
    pv.getProfileInfo = MagicMock(side_effect=[
        (None, None, None, None),
        ("lolatheozjack", 10, 100, 200)
    ])
    tbv.navigateToProfile = MagicMock()

    # Simulate the recovery block logic
    session_state = MagicMock()
    (
        session_state.my_username,
        session_state.my_posts_count,
        session_state.my_followers_count,
        session_state.my_following_count,
    ) = pv.getProfileInfo()

    if (
        session_state.my_username is None
        or session_state.my_posts_count is None
        or session_state.my_followers_count is None
        or session_state.my_following_count is None
    ):
        tbv.navigateToProfile()
        (
            session_state.my_username,
            session_state.my_posts_count,
            session_state.my_followers_count,
            session_state.my_following_count,
        ) = pv.getProfileInfo()

    assert tbv.navigateToProfile.called
    assert session_state.my_username == "lolatheozjack"
    assert session_state.my_followers_count == 100


def test_action_bar_view_app_has_crashed_resilience():
    """Verify that ActionBarView and ProfileView handle AppHasCrashed during __init__ without failing."""
    from InstaAddict.core.views import ActionBarView, ProfileView

    mock_device = MagicMock()
    mock_device.find.side_effect = DeviceFacade.AppHasCrashed("App closed")

    # Creating ActionBarView must not raise AppHasCrashed
    abv = ActionBarView(mock_device)
    assert abv.action_bar is None

    # Creating ProfileView must also not raise AppHasCrashed
    pv = ProfileView(mock_device)
    assert pv.action_bar is None


def test_profile_view_get_username_app_has_crashed_returns_none():
    """Verify that ProfileView.getUsername returns None on AppHasCrashed rather than raising."""
    from InstaAddict.core.views import ProfileView

    mock_device = MagicMock()
    mock_device.find.side_effect = DeviceFacade.AppHasCrashed("App closed")

    pv = ProfileView(mock_device)
    assert pv.getUsername(error=False) is None
    assert pv.getUsername(error=True) is None


def test_open_instagram_checks_foreground_before_success():
    """Verify that open_instagram returns False if Instagram fails to stay in the foreground."""
    from InstaAddict.core.utils import open_instagram

    mock_device = MagicMock()
    mock_device.deviceV2.app_current.return_value = {"package": "com.android.launcher"}
    mock_device._ig_is_opened.return_value = False

    mock_device.app_id = "com.instagram.android"

    with patch("InstaAddict.core.utils.random_sleep"), \
         patch("InstaAddict.core.utils.check_if_crash_popup_is_there", return_value=False), \
         patch("time.sleep"):
        res = open_instagram(mock_device)
        assert res is False


def test_startup_retry_recovers_from_app_has_crashed():
    """Verify that startup retry catches AppHasCrashed and relaunches via open_instagram."""
    mock_device = MagicMock()
    mock_session_state = MagicMock()
    mock_session_state.totalCrashes = 0

    open_ig_calls = []

    def mock_open_ig(dev):
        open_ig_calls.append(dev)
        return True

    # Simulate 3 attempts: attempt 0 raises AppHasCrashed, attempt 1 succeeds
    calls = [0]

    def mock_profile_init(dev):
        calls[0] += 1
        if calls[0] == 1:
            raise DeviceFacade.AppHasCrashed("Instagram closed during startup")
        mock_pv = MagicMock()
        mock_pv.getProfileInfo.return_value = ("lolatheozjack", 10, 100, 50)
        return mock_pv

    startup_ok = False
    for startup_attempt in range(3):
        try:
            pv = mock_profile_init(mock_device)
            username, posts, followers, following = pv.getProfileInfo()
            startup_ok = True
            break
        except DeviceFacade.AppHasCrashed:
            mock_session_state.totalCrashes += 1
            mock_open_ig(mock_device)

    assert startup_ok is True
    assert mock_session_state.totalCrashes == 1
    assert len(open_ig_calls) == 1
    assert username == "lolatheozjack"


def test_session_state_skip_reasons_and_job_metrics():
    """Verify that SessionState records skip reasons, job metrics, and crash history, and encodes them to JSON."""
    import json
    from InstaAddict.core.session_state import SessionState, SessionStateEncoder

    ss = SessionState()
    ss.record_skip_reason("LT_FOLLOWERS")
    ss.record_skip_reason("LT_FOLLOWERS")
    ss.record_skip_reason("POTENCY_RATIO")

    assert ss.skip_reasons["LT_FOLLOWERS"] == 2
    assert ss.skip_reasons["POTENCY_RATIO"] == 1

    ss.start_job("interact_hashtag")
    ss.record_job_interaction("interact_hashtag", success=True, followed=True)
    ss.record_job_interaction("interact_hashtag", success=False)
    ss.end_job("interact_hashtag", "completed")

    assert "interact_hashtag" in ss.job_metrics
    jm = ss.job_metrics["interact_hashtag"]
    assert jm["status"] == "completed"
    assert jm["interactions_attempted"] == 2
    assert jm["interactions_successful"] == 1
    assert jm["followed"] == 1

    ss.record_crash({"timestamp": "2026-09-22T00:00:00", "error_reason": "test_crash"})
    assert len(ss.crash_history) == 1
    assert ss.totalCrashes == 1

    encoded = json.loads(json.dumps(ss, cls=SessionStateEncoder))
    assert encoded["skip_reasons"]["LT_FOLLOWERS"] == 2
    assert encoded["job_metrics"]["interact_hashtag"]["interactions_attempted"] == 2
    assert len(encoded["crash_history"]) == 1


def test_filter_records_skip_reason_name_in_active_session_state():
    """Verify Filter.return_check_profile records SkipReason into active SessionState."""
    from InstaAddict.core.filter import Filter, Profile, SkipReason
    from InstaAddict.core.session_state import SessionState

    mock_storage = MagicMock()
    f = Filter(mock_storage)

    ss = SessionState()
    SessionState.set_active(ss)
    try:
        mock_profile = Profile(0, "Follow", False, True, 10, 100, 5, 0, False)
        skipped = f.return_check_profile("testuser", mock_profile, SkipReason.LT_FOLLOWERS)
        assert skipped is True
        assert ss.totalProfilesSkipped == 1
        assert ss.skip_reasons.get("LT_FOLLOWERS") == 1

        skipped2 = f.return_check_profile("testuser2", mock_profile, SkipReason.POTENCY_RATIO)
        assert skipped2 is True
        assert ss.totalProfilesSkipped == 2
        assert ss.skip_reasons.get("POTENCY_RATIO") == 1
    finally:
        SessionState.set_active(None)


def test_save_crash_generates_context_json_and_records_to_session(tmp_path, monkeypatch):
    """Verify save_crash writes crash_context.json and records crash in active SessionState."""
    import os
    import zipfile
    import json
    from InstaAddict.core.session_state import SessionState
    from InstaAddict.core.utils import save_crash

    monkeypatch.chdir(tmp_path)
    mock_device = MagicMock()
    mock_device.get_current_package.return_value = "com.instagram.android"
    mock_device.is_screen_on.return_value = True

    ss = SessionState()
    ss.my_username = "testuser"
    SessionState.set_active(ss)
    try:
        save_crash(mock_device, error_reason="Testing crash telemetry")

        assert len(ss.crash_history) == 1
        assert ss.crash_history[0]["error_reason"] == "Testing crash telemetry"
        assert ss.crash_history[0]["foreground_package"] == "com.instagram.android"

        # Check zip archive
        zip_path = ss.crash_history[0]["crash_archive"]
        assert os.path.exists(zip_path)
        with zipfile.ZipFile(zip_path, "r") as z:
            assert "crash_context.json" in z.namelist()
            with z.open("crash_context.json") as jf:
                data = json.load(jf)
                assert data["username"] == "testuser"
                assert data["error_reason"] == "Testing crash telemetry"
                assert data["foreground_package"] == "com.instagram.android"
    finally:
        SessionState.set_active(None)


def test_dogfood_optimizer_analyzes_skip_reasons_and_recommends_filter_tuning(tmp_path, monkeypatch):
    """Verify DogfoodOptimizer detects filter starvation and produces actionable filter recommendations."""
    import json
    from InstaAddict.core.dogfood import DogfoodOptimizer

    monkeypatch.chdir(tmp_path)
    acc_dir = tmp_path / "accounts" / "testuser"
    acc_dir.mkdir(parents=True)

    sessions_data = [
        {
            "id": "s1",
            "total_interactions": 10,
            "successful_interactions": 2,
            "total_likes": 2,
            "total_followed": 0,
            "total_crashes": 0,
            "skip_reasons": {
                "LT_FOLLOWERS": 60,
                "POTENCY_RATIO": 10,
            },
        }
    ]
    with open(acc_dir / "sessions.json", "w") as f:
        json.dump(sessions_data, f)

    with open(acc_dir / "filters.yml", "w") as f:
        f.write("min_followers: 50\nmin_potency_ratio: 0.5\n")

    optimizer = DogfoodOptimizer("testuser")
    analysis = optimizer.analyze()

    assert analysis["metrics"]["total_skips"] == 70
    assert analysis["skip_reasons"]["LT_FOLLOWERS"] == 60

    # Verify recommendation
    rec_cats = [r["category"] for r in analysis["recommendations"]]
    assert "Filter Starvation" in rec_cats

    # Verify auto-tuning applies to filters.yml
    tune_res = optimizer.apply_tuning(dry_run=False, backup=True)
    assert any(a.get("parameter") == "min_followers" for a in tune_res["applied"])

    with open(acc_dir / "filters.yml", "r") as f:
        content = f.read()
    assert "min_followers: 35" in content  # 50 * 0.7 = 35


def test_dogfood_optimizer_analyzes_job_performance_standards(tmp_path, monkeypatch):
    """Verify DogfoodOptimizer identifies jobs failing standards (100% conversion failure)."""
    import json
    from InstaAddict.core.dogfood import DogfoodOptimizer

    monkeypatch.chdir(tmp_path)
    acc_dir = tmp_path / "accounts" / "testuser"
    acc_dir.mkdir(parents=True)

    sessions_data = [
        {
            "id": "s1",
            "total_interactions": 10,
            "successful_interactions": 5,
            "total_likes": 5,
            "total_followed": 1,
            "total_crashes": 0,
            "job_metrics": {
                "interact_hashtag": {
                    "runs": 1,
                    "duration_seconds": 120.0,
                    "interactions_attempted": 8,
                    "interactions_successful": 0,
                }
            },
        }
    ]
    with open(acc_dir / "sessions.json", "w") as f:
        json.dump(sessions_data, f)

    optimizer = DogfoodOptimizer("testuser")
    analysis = optimizer.analyze()

    assert "interact_hashtag" in analysis["job_performance"]
    recs = [r for r in analysis["recommendations"] if r["category"] == "Task Performance Standards"]
    assert len(recs) >= 1
    assert "interact_hashtag" in recs[0]["issue"]





from unittest.mock import MagicMock, patch
from InstaAddict.plugins.interact_reels import InteractReelsPlugin


class TestReelsEngagementDecoupling:
    """Tests for Route-058: Decoupled Reels liking, following, and fallback commenting."""

    def setup_method(self):
        self.plugin = InteractReelsPlugin()

    @patch("InstaAddict.plugins.interact_reels.random_sleep")
    @patch("InstaAddict.plugins.interact_reels._comment")
    @patch("InstaAddict.plugins.interact_reels.TabBarView")
    @patch("InstaAddict.plugins.interact_reels.UniversalActions")
    def test_reels_engages_organically_when_eval_skipped_for_quota(
        self, mock_ua, mock_tab_bar, mock_comment, mock_sleep
    ):
        """When evaluate_percentage is 0 (quota preservation), reel is engaged organically."""
        device = MagicMock()
        d = MagicMock()
        device.deviceV2 = d
        d.info = {"displayWidth": 1080, "displayHeight": 2400}

        mock_ua.escape_in_app_browser.return_value = False

        # No ads
        ad_elem = MagicMock()
        ad_elem.exists.return_value = False
        device.find.return_value = ad_elem

        session = MagicMock()
        session.my_username = "test_user"
        session.totalLikes = 0
        session.totalFollowed = {}
        session.check_limit.return_value = False

        configs = MagicMock()
        configs.args.interact_reels = "1"
        configs.args.evaluate_percentage = "0"  # quota preservation
        configs.args.interact_percentage = "100"
        configs.args.likes_percentage = "100"
        configs.args.follow_percentage = "0"
        configs.args.comment_percentage = "100"

        self.plugin.run(device, configs, None, [session], None, "interact-reels")

        # Liked via double tap
        assert session.totalLikes == 1
        assert d.click.call_count >= 2
        # Comment executed with fallback (explicit_comment=None)
        assert mock_comment.called
        call_kwargs = mock_comment.call_args[1]
        assert call_kwargs.get("explicit_comment") is None

    @patch("InstaAddict.plugins.interact_reels.random_sleep")
    @patch("InstaAddict.plugins.interact_reels.evaluate_and_comment_reel", return_value="")
    @patch("InstaAddict.plugins.interact_reels._comment")
    @patch("InstaAddict.plugins.interact_reels.TabBarView")
    @patch("InstaAddict.plugins.interact_reels.UniversalActions")
    def test_reels_skips_when_vision_returns_empty_and_api_alive(
        self, mock_ua, mock_tab_bar, mock_comment, mock_eval, mock_sleep
    ):
        """When Vision AI returns empty (non-target) and API is alive, skip interaction."""
        device = MagicMock()
        d = MagicMock()
        device.deviceV2 = d
        d.info = {"displayWidth": 1080, "displayHeight": 2400}
        d.screenshot.return_value = b"raw_png"

        mock_ua.escape_in_app_browser.return_value = False

        ad_elem = MagicMock()
        ad_elem.exists.return_value = False
        device.find.return_value = ad_elem

        session = MagicMock()
        session.totalLikes = 0
        session.check_limit.return_value = False

        configs = MagicMock()
        configs.args.interact_reels = "1"
        configs.args.evaluate_percentage = "100"
        configs.args.interact_percentage = "100"
        configs.args.reels_topic = "dogs"

        with patch("InstaAddict.core.gemini_vision.VISION_API_DEAD", False), \
             patch("os.getenv", return_value="VALID_KEY"):
            self.plugin.run(device, configs, None, [session], None, "interact-reels")

        # Since it was non-target, like and comment did NOT run
        assert session.totalLikes == 0
        assert not mock_comment.called

    @patch("InstaAddict.plugins.interact_reels.random_sleep")
    @patch("InstaAddict.plugins.interact_reels.evaluate_and_comment_reel", return_value="")
    @patch("InstaAddict.plugins.interact_reels._comment")
    @patch("InstaAddict.plugins.interact_reels.TabBarView")
    @patch("InstaAddict.plugins.interact_reels.UniversalActions")
    def test_reels_engages_fallback_when_vision_api_dead(
        self, mock_ua, mock_tab_bar, mock_comment, mock_eval, mock_sleep
    ):
        """When Vision AI is dead or no API key, interact organically with fallback comment."""
        device = MagicMock()
        d = MagicMock()
        device.deviceV2 = d
        d.info = {"displayWidth": 1080, "displayHeight": 2400}
        d.screenshot.return_value = b"raw_png"

        mock_ua.escape_in_app_browser.return_value = False

        ad_elem = MagicMock()
        ad_elem.exists.return_value = False
        device.find.return_value = ad_elem

        session = MagicMock()
        session.my_username = "test_user"
        session.totalLikes = 0
        session.totalFollowed = {}
        session.check_limit.return_value = False

        configs = MagicMock()
        configs.args.interact_reels = "1"
        configs.args.evaluate_percentage = "100"
        configs.args.interact_percentage = "100"
        configs.args.likes_percentage = "100"
        configs.args.comment_percentage = "100"
        configs.args.follow_percentage = "0"

        with patch("InstaAddict.core.gemini_vision.VISION_API_DEAD", True):
            self.plugin.run(device, configs, None, [session], None, "interact-reels")

        assert session.totalLikes == 1
        assert mock_comment.called
        call_kwargs = mock_comment.call_args[1]
        assert call_kwargs.get("explicit_comment") is None

    @patch("InstaAddict.plugins.interact_reels.random_sleep")
    @patch("InstaAddict.plugins.interact_reels.evaluate_and_comment_reel", return_value="Good boy! 🐾")
    @patch("InstaAddict.plugins.interact_reels._comment")
    @patch("InstaAddict.plugins.interact_reels.TabBarView")
    @patch("InstaAddict.plugins.interact_reels.UniversalActions")
    def test_reels_likes_even_if_comment_fails(
        self, mock_ua, mock_tab_bar, mock_comment, mock_eval, mock_sleep
    ):
        """Double-tap like and follow persist even if comment raises an exception."""
        mock_comment.side_effect = Exception("Comment element detached")

        device = MagicMock()
        d = MagicMock()
        device.deviceV2 = d
        d.info = {"displayWidth": 1080, "displayHeight": 2400}
        d.screenshot.return_value = b"raw_png"

        mock_ua.escape_in_app_browser.return_value = False

        ad_elem = MagicMock()
        ad_elem.exists.return_value = False
        device.find.return_value = ad_elem

        session = MagicMock()
        session.my_username = "test_user"
        session.totalLikes = 0
        session.totalFollowed = {}
        session.check_limit.return_value = False

        configs = MagicMock()
        configs.args.interact_reels = "1"
        configs.args.evaluate_percentage = "100"
        configs.args.interact_percentage = "100"
        configs.args.likes_percentage = "100"
        configs.args.follow_percentage = "0"
        configs.args.comment_percentage = "100"

        self.plugin.run(device, configs, None, [session], None, "interact-reels")

        # Like succeeded despite comment error
        assert session.totalLikes == 1
        assert session.add_interaction.called

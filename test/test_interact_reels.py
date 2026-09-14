import unittest
from unittest.mock import MagicMock, patch

from InstaAddict.plugins.interact_reels import InteractReelsPlugin


class TestInteractReelsPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = InteractReelsPlugin()

    def test_plugin_arguments(self):
        """Verify all argument definitions including --reels-topic."""
        args_by_name = {arg["arg"]: arg for arg in self.plugin.arguments}
        self.assertIn("--interact-reels", args_by_name)
        self.assertIn("--evaluate-percentage", args_by_name)
        self.assertIn("--reels-topic", args_by_name)

        topic_arg = args_by_name["--reels-topic"]
        self.assertEqual(topic_arg["default"], "dogs or animals")
        self.assertEqual(topic_arg["metavar"], "dogs or animals")

    @patch("InstaAddict.plugins.interact_reels.evaluate_and_comment_reel")
    @patch("InstaAddict.plugins.interact_reels.TabBarView")
    @patch("InstaAddict.plugins.interact_reels.UniversalActions")
    def test_reels_topic_passed_to_vlm(self, mock_actions, mock_tab_bar, mock_eval):
        """Verifies custom --reels-topic is forwarded to evaluate_and_comment_reel."""
        mock_eval.return_value = ""
        mock_actions.escape_in_app_browser.return_value = False

        device = MagicMock()
        device.deviceV2.info = {"displayWidth": 1080, "displayHeight": 2400}
        device.deviceV2.screenshot.return_value = b"fake_screenshot_bytes"

        # Mock no ad presence
        device.find.return_value.exists.return_value = False

        configs = MagicMock()
        configs.args.interact_reels = "1"
        configs.args.evaluate_percentage = 100
        configs.args.reels_topic = "surfing or beach"

        self.plugin.run(device, configs, None, [MagicMock()], None, "interact-reels")

        self.assertTrue(mock_eval.called)
        call_kwargs = mock_eval.call_args[1]
        self.assertEqual(call_kwargs.get("topic"), "surfing or beach")

    @patch("InstaAddict.plugins.interact_reels.evaluate_and_comment_reel")
    @patch("InstaAddict.plugins.interact_reels.TabBarView")
    @patch("InstaAddict.plugins.interact_reels.UniversalActions")
    def test_reels_topic_default_fallback(self, mock_actions, mock_tab_bar, mock_eval):
        """Verifies default topic is used when reels_topic attribute is absent or None."""
        mock_eval.return_value = ""
        mock_actions.escape_in_app_browser.return_value = False

        device = MagicMock()
        device.deviceV2.info = {"displayWidth": 1080, "displayHeight": 2400}
        device.deviceV2.screenshot.return_value = b"fake_screenshot_bytes"
        device.find.return_value.exists.return_value = False

        configs = MagicMock()
        configs.args.interact_reels = "1"
        configs.args.evaluate_percentage = 100
        # Delete or set None for reels_topic
        configs.args.reels_topic = None

        self.plugin.run(device, configs, None, [MagicMock()], None, "interact-reels")

        self.assertTrue(mock_eval.called)
        call_kwargs = mock_eval.call_args[1]
        self.assertEqual(call_kwargs.get("topic"), "dogs or animals")


if __name__ == "__main__":
    unittest.main()

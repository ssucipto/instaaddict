import os
import json
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from InstaAddict.core.storage import CommentMemory
from InstaAddict.core.gemini_vision import (
    classify_sentiment,
    generate_sentiment_fallback,
    FALLBACK_COMMENTS_BY_SENTIMENT,
    SENTIMENT_SYMPATHETIC,
    SENTIMENT_CELEBRATORY,
    SENTIMENT_PLAYFUL,
    SENTIMENT_INQUISITIVE,
    SENTIMENT_APPRECIATIVE,
    get_vision_comment,
    evaluate_and_comment_reel,
    _sanitize_response,
)
from InstaAddict.core.interaction import _comment, load_random_comment
from InstaAddict.core.views import MediaType


class TestCommentMemory:
    """Test suite for CommentMemory persistence and anti-repetition Jaccard similarity."""

    def test_comment_memory_persistence_and_cap(self, tmp_path):
        account_dir = tmp_path / "accounts" / "test_user"
        account_dir.mkdir(parents=True)
        mem = CommentMemory(str(account_dir))

        # Add 550 comments
        for i in range(550):
            mem.add_comment(f"Comment number {i} for testing", target_username=f"user_{i}", sentiment="APPRECIATIVE")

        # Verify max cap of 500
        assert len(mem.comments) == 500
        assert mem.comments[-1]["comment"] == "Comment number 549 for testing"

        # Verify disk persistence
        history_file = account_dir / "comment_history.json"
        assert history_file.is_file()
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 500

        # Reload in a new instance and verify
        mem2 = CommentMemory(str(account_dir))
        assert len(mem2.comments) == 500
        assert mem2.get_recent_comments(limit=5)[-1] == "Comment number 549 for testing"

    def test_jaccard_similarity_check(self, tmp_path):
        account_dir = tmp_path / "accounts" / "test_sim"
        account_dir.mkdir(parents=True)
        mem = CommentMemory(str(account_dir))

        mem.add_comment("Look at that adorable pup playing in the fresh autumn leaves!")

        # High similarity test
        assert mem.is_similar_to_recent("Look at that adorable pup playing in the autumn leaves!", threshold=0.55) is True
        # Exact match (case insensitive)
        assert mem.is_similar_to_recent("look at that adorable pup playing in the fresh autumn leaves!") is True
        # Low similarity test (distinct thought)
        assert mem.is_similar_to_recent("Such a peaceful sunset walk by the calm beach today.", threshold=0.55) is False


class TestSentimentClassifier:
    """Test suite for 5-bucket emotional tone classifier."""

    def test_sympathetic_sentiment(self):
        assert classify_sentiment("Rest in peace sweet angel, run free over the rainbow bridge") == SENTIMENT_SYMPATHETIC
        assert classify_sentiment("Heartbroken today, heading into emergency vet surgery") == SENTIMENT_SYMPATHETIC
        assert classify_sentiment("Fighting cancer with all we got, please keep us in your prayers") == SENTIMENT_SYMPATHETIC

    def test_celebratory_sentiment(self):
        assert classify_sentiment("Happy 3rd birthday to our handsome boy!") == SENTIMENT_CELEBRATORY
        assert classify_sentiment("Celebrating our 2-year gotcha day anniversary today!") == SENTIMENT_CELEBRATORY
        assert classify_sentiment("We won first place at the agility championship!") == SENTIMENT_CELEBRATORY

    def test_playful_sentiment(self):
        assert classify_sentiment("Total zoomies mode engaged at 3 AM! Complete chaos") == SENTIMENT_PLAYFUL
        assert classify_sentiment("Caught red-handed stealing socks again, peak derp face") == SENTIMENT_PLAYFUL
        assert classify_sentiment("Little mischief maker causing trouble with the hose") == SENTIMENT_PLAYFUL

    def test_inquisitive_sentiment(self):
        assert classify_sentiment("Any recommendations for durable chew toys?") == SENTIMENT_INQUISITIVE
        assert classify_sentiment("Which harness do you reckon is best for hiking?") == SENTIMENT_INQUISITIVE
        assert classify_sentiment("What do you all think about raw feeding?") == SENTIMENT_INQUISITIVE

    def test_appreciative_default(self):
        assert classify_sentiment("Soaking up the golden hour sunshine on our afternoon walk") == SENTIMENT_APPRECIATIVE
        assert classify_sentiment("Cozy Sunday morning cuddles on the sofa") == SENTIMENT_APPRECIATIVE
        assert classify_sentiment("") == SENTIMENT_APPRECIATIVE


class TestFallbackCommentsLibrary:
    """Test suite for 100+ fallback comments library quality and freshness."""

    def test_library_size_and_categories(self):
        total_comments = sum(len(comments) for comments in FALLBACK_COMMENTS_BY_SENTIMENT.values())
        assert total_comments >= 100
        for sentiment in [
            SENTIMENT_SYMPATHETIC,
            SENTIMENT_CELEBRATORY,
            SENTIMENT_PLAYFUL,
            SENTIMENT_INQUISITIVE,
            SENTIMENT_APPRECIATIVE,
        ]:
            assert sentiment in FALLBACK_COMMENTS_BY_SENTIMENT
            assert len(FALLBACK_COMMENTS_BY_SENTIMENT[sentiment]) >= 20

    def test_clean_sanitized_templates(self):
        for sentiment, templates in FALLBACK_COMMENTS_BY_SENTIMENT.items():
            for t in templates:
                # No markdown asterisks
                assert "*" not in t
                # No em-dashes
                assert "—" not in t and "–" not in t
                # Length within 5 to 25 words
                words = t.split()
                assert 4 <= len(words) <= 25

    def test_generate_sentiment_fallback_with_memory(self, tmp_path):
        account_dir = tmp_path / "accounts" / "test_fb"
        account_dir.mkdir(parents=True)
        mem = CommentMemory(str(account_dir))

        # Pick first 5 comments from playful bucket and add to memory
        playful_bucket = FALLBACK_COMMENTS_BY_SENTIMENT[SENTIMENT_PLAYFUL]
        for c in playful_bucket[:5]:
            mem.add_comment(c)

        # Generate fallback
        chosen = generate_sentiment_fallback(sentiment=SENTIMENT_PLAYFUL, memory=mem)
        assert chosen in playful_bucket
        # Ensure it didn't pick any of the 5 already in memory
        assert chosen not in playful_bucket[:5]


class TestGeminiVisionCommenting:
    """Test suite for get_vision_comment multimodal context and error resilience."""

    @patch("InstaAddict.core.gemini_vision.genai.GenerativeModel")
    @patch("InstaAddict.core.gemini_vision.genai.configure")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_test_key"})
    def test_multimodal_caption_and_author_prompting(self, mock_cfg, mock_model_cls, tmp_path):
        import InstaAddict.core.gemini_vision as gv
        gv.VISION_API_DEAD = False
        gv.SESSION_API_CALLS = 0

        mock_model = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "Those soulful eyes are just melting my heart right now mate!"
        mock_resp.candidates = [MagicMock(finish_reason="STOP")]
        mock_model.generate_content.return_value = mock_resp
        mock_model_cls.return_value = mock_model

        mock_device = MagicMock()
        mock_device.take_screenshot.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200

        # Create temporary valid PNG in memory
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        mock_device.take_screenshot.return_value = buf.getvalue()

        result = get_vision_comment(
            mock_device,
            caption="Happy 2nd birthday to our beloved golden boy!",
            author="golden_life",
            community_comments=["So cute!", "Happy bday!"],
            account_name=str(tmp_path / "acc_multi"),
        )

        assert "soulful eyes" in result
        # Check system prompt received author and caption
        init_kwargs = mock_model_cls.call_args[1]
        system_instruction = init_kwargs.get("system_instruction", "")
        assert "@golden_life" in system_instruction
        assert "Happy 2nd birthday" in system_instruction
        assert "6 to 18 words" in system_instruction

    @patch("InstaAddict.core.gemini_vision.genai.GenerativeModel")
    @patch("InstaAddict.core.gemini_vision.genai.configure")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_test_key"})
    def test_safety_filter_text_recovery_pass(self, mock_cfg, mock_model_cls, tmp_path):
        import InstaAddict.core.gemini_vision as gv
        gv.VISION_API_DEAD = False
        gv.SESSION_API_CALLS = 0

        # First call on image blocked by safety filter (finish_reason=2)
        mock_img_resp = MagicMock()
        mock_img_resp.candidates = [MagicMock(finish_reason=2)]
        type(mock_img_resp).text = property(lambda self: (_ for _ in ()).throw(ValueError("Safety block")))

        # Second call (text-only recovery pass) succeeds
        mock_text_resp = MagicMock()
        mock_text_resp.candidates = [MagicMock(finish_reason="STOP")]
        mock_text_resp.text = "Sending the biggest warm cuddles and gentle thoughts your way mate."

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = [mock_img_resp, mock_text_resp]
        mock_model_cls.return_value = mock_model

        mock_device = MagicMock()
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        mock_device.take_screenshot.return_value = buf.getvalue()

        result = get_vision_comment(
            mock_device,
            caption="Rest in peace sweet boy, we will miss you forever",
            author="doggo_mom",
            account_name=str(tmp_path / "acc_recov"),
        )

        assert "warm cuddles" in result
        assert mock_model.generate_content.call_count == 2


class TestInteractionFocusAndTyping:
    """Test suite for _comment focus-before-type and community comment handling."""

    def test_comment_focus_tap_and_successful_post(self):
        mock_device = MagicMock()
        mock_device.device_id = "emulator-5554"
        mock_device.app_id = "com.instagram.android"
        mock_device.deviceV2.serial = "emulator-5554"
        mock_device.get_info.return_value = {"displayWidth": 1080, "displayHeight": 1920}

        # Mock comment button
        mock_comment_btn = MagicMock()
        mock_comment_btn.exists.return_value = True

        # Mock comment box with click method
        mock_comment_box = MagicMock()
        mock_comment_box.exists.return_value = True

        # Mock post button
        mock_post_btn = MagicMock()
        mock_post_btn.exists.return_value = True

        # Mock posted verification
        mock_posted_text = MagicMock()
        mock_posted_text.exists.return_value = True

        def find_side_effect(*args, **kwargs):
            if "descriptionMatches" in kwargs and "(?i).*" in kwargs["descriptionMatches"]:
                return mock_posted_text
            if "resourceIdMatches" in kwargs and "layout_comment_thread_post_button" in kwargs["resourceIdMatches"]:
                return mock_post_btn
            if "resourceId" in kwargs and "layout_comment_thread_post_button" in kwargs["resourceId"]:
                return mock_post_btn
            if "resourceId" in kwargs and "layout_comment_thread_edittext" in kwargs["resourceId"]:
                return mock_comment_box
            if "resourceIdMatches" in kwargs and "row_feed_button_comment" in kwargs["resourceIdMatches"]:
                return mock_comment_btn
            mock_elem = MagicMock()
            mock_elem.exists.return_value = False
            return mock_elem

        mock_device.find.side_effect = find_side_effect
        mock_device.find_all.return_value = []

        mock_session_state = MagicMock()
        mock_session_state.check_limit.return_value = False
        mock_session_state.totalComments = 0

        mock_args = MagicMock()
        mock_args.dont_type = False
        mock_args.app_id = "com.instagram.android"

        with patch("InstaAddict.core.interaction.get_vision_comment", return_value="What a proper little champion mate!"), \
             patch("InstaAddict.core.views.UniversalActions.close_keyboard"):
            success = _comment(
                mock_device,
                my_username="test_runner",
                comment_percentage=100,
                args=mock_args,
                session_state=mock_session_state,
                media_type=MediaType.PHOTO,
                caption="Look at this handsome pup enjoying his walk",
                author="jack_russell",
            )

            assert success is True
            # Assert focus tap was called on comment_box before set_text
            assert mock_comment_box.click.called
            assert mock_comment_box.set_text.called
            assert mock_session_state.totalComments == 1

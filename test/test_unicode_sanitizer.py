import pytest
import re
from unittest.mock import MagicMock
from InstaAddict.core.gemini_vision import _sanitize_response, _safe_extract_text
from InstaAddict.core.device_facade import _split_into_grapheme_clusters


class TestUnicodeSanitizer:
    """Validates stripping of hidden zero-width Unicode characters, ZWJs, and skin-tone modifiers."""

    def test_strip_zwj_and_zero_width_spaces(self):
        # A literal composite emoji with ZWJs (U+200D)
        # 👨 (U+1F468) + ZWJ (U+200D) + 👩 (U+1F469) + ZWJ (U+200D) + 👧 (U+1F467)
        raw_composite = "Amazing family \U0001F468\u200D\U0001F469\u200D\U0001F467 at sunset! \u200B\uFEFF"
        sanitized = _sanitize_response(raw_composite)

        # ZWJ (U+200D), ZWSP (U+200B), and BOM (U+FEFF) must all be stripped
        assert "\u200D" not in sanitized
        assert "\u200B" not in sanitized
        assert "\uFEFF" not in sanitized
        assert "Amazing family" in sanitized
        assert "at sunset!" in sanitized

    def test_strip_skin_tone_modifiers(self):
        # Thumbs up with medium skin tone modifier (U+1F44D + U+1F3FD)
        raw_modifier = "Great job! \U0001F44D\U0001F3FD"
        sanitized = _sanitize_response(raw_modifier)
        # Skin-tone modifier is stripped, leaving the base emoji intact
        assert "\U0001F3FD" not in sanitized
        assert "Great job!" in sanitized
        assert "\U0001F44D" in sanitized

    def test_blocks_llm_outings(self):
        raw_outing = "As an AI, I really love this picture!"
        sanitized = _sanitize_response(raw_outing)
        assert sanitized == ""

    def test_safe_extract_text_normal(self):
        mock_response = MagicMock()
        mock_response.text = "Beautiful beach view"
        mock_response.candidates = [MagicMock(finish_reason=1)]
        res = _safe_extract_text(mock_response)
        assert res == "Beautiful beach view"

    def test_safe_extract_text_safety_blocked(self):
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock(finish_reason=2)] # 2 = SAFETY
        # Should return empty string without raising ValueError
        res = _safe_extract_text(mock_response)
        assert res == ""

    def test_safe_extract_text_none_or_exception(self):
        res = _safe_extract_text(None)
        assert res == ""

        mock_error_resp = MagicMock()
        type(mock_error_resp).text = property(lambda self: (_ for _ in ()).throw(ValueError("Part missing")))
        mock_error_resp.candidates = []
        res = _safe_extract_text(mock_error_resp)
        assert res == ""


class TestGraphemeClusterPreservation:
    """Verifies that device_facade splits words into atomic grapheme units without severing emojis."""

    def test_standard_ascii_words(self):
        clusters = _split_into_grapheme_clusters("hello")
        assert clusters == ["h", "e", "l", "l", "o"]

    def test_emoji_with_punctuation(self):
        clusters = _split_into_grapheme_clusters("dog!🐶")
        assert clusters == ["d", "o", "g", "!", "🐶"]

    def test_composite_emoji_kept_atomic(self):
        # When an emoji is encountered, it should be treated as an atomic cluster
        composite = "\U0001F468\u200D\U0001F469\u200D\U0001F467"
        clusters = _split_into_grapheme_clusters(composite)
        assert len(clusters) == 1
        assert clusters[0] == composite

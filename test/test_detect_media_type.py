"""
Tests for PostsViewList.detect_media_type() -- E1 upstream cherry-pick.

Verifies that the modern IG 447+ carousel format "Photo N of M by User, likes"
is correctly classified as CAROUSEL before the plain ^Photo branch fires.
Also validates backward compat with legacy carousel and other media types.
"""
import pytest

from InstaAddict.core.views import MediaType, PostsViewList


class TestDetectMediaType:
    """Unit tests for the static detect_media_type method."""

    def test_none_returns_none_tuple(self):
        """None input -> (None, None) -- caller must handle missing description."""
        media_type, count = PostsViewList.detect_media_type(None)
        assert media_type is None
        assert count is None

    def test_empty_comma_returns_unknown(self):
        """Comma-only or whitespace-only -> UNKNOWN type."""
        media_type, count = PostsViewList.detect_media_type(",")
        assert media_type == MediaType.UNKNOWN

    def test_photo(self):
        """Single photo description -> PHOTO, count=1."""
        media_type, count = PostsViewList.detect_media_type(
            "Photo by username, 100 likes"
        )
        assert media_type == MediaType.PHOTO
        assert count == 1

    def test_hidden_photo(self):
        """Hidden photo -> PHOTO."""
        media_type, count = PostsViewList.detect_media_type("Hidden Photo")
        assert media_type == MediaType.PHOTO

    def test_video(self):
        """Single video -> VIDEO, count=1."""
        media_type, count = PostsViewList.detect_media_type("Video by username")
        assert media_type == MediaType.VIDEO
        assert count == 1

    def test_reel(self):
        """Reel description -> REEL, count=1."""
        media_type, count = PostsViewList.detect_media_type("Reel by username")
        assert media_type == MediaType.REEL
        assert count == 1

    def test_igtv(self):
        """IGTV description -> IGTV, count=1."""
        media_type, count = PostsViewList.detect_media_type("IGTV by username")
        assert media_type == MediaType.IGTV
        assert count == 1

    # E1: IG 447+ modern carousel format

    def test_carousel_modern_photo_format(self):
        """IG 447+: 'Photo 1 of 4 by user, 2280 likes' -> CAROUSEL, obj_count=4.

        Previously matched ^Photo first and returned PHOTO -- this is the core bug
        fixed by upstream commit f32620c that this test guards against regression.
        """
        media_type, count = PostsViewList.detect_media_type(
            "Photo 1 of 4 by username, 2280 likes"
        )
        assert media_type == MediaType.CAROUSEL, (
            "Modern carousel 'Photo N of M' must be classified as CAROUSEL, not PHOTO"
        )
        assert count == 4

    def test_carousel_modern_video_format(self):
        """IG 447+: 'Video 2 of 3 by user' -> CAROUSEL, obj_count=3."""
        media_type, count = PostsViewList.detect_media_type("Video 2 of 3 by username")
        assert media_type == MediaType.CAROUSEL
        assert count == 3

    def test_carousel_modern_case_insensitive(self):
        """Regex must be case-insensitive: 'photo 1 of 5' -> CAROUSEL, obj_count=5."""
        media_type, count = PostsViewList.detect_media_type("photo 1 of 5 by user")
        assert media_type == MediaType.CAROUSEL
        assert count == 5

    # Legacy carousel format (backward compat)

    def test_carousel_legacy_format(self):
        """Legacy: '2 photos, 1 video' -> CAROUSEL, obj_count=3 (photos + videos)."""
        media_type, count = PostsViewList.detect_media_type("2 photos, 1 video")
        assert media_type == MediaType.CAROUSEL
        assert count == 3

    def test_carousel_legacy_photos_only(self):
        """Legacy: '5 photos' -> CAROUSEL, obj_count=5."""
        media_type, count = PostsViewList.detect_media_type("5 photos")
        assert media_type == MediaType.CAROUSEL
        assert count == 5

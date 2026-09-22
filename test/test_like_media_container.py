"""
Tests for PostsViewList._describes_a_post() and _get_media_container() -- E2 upstream cherry-pick.

Verifies that:
- _describes_a_post() checks outer get_desc() first, then falls back to inner image child
- _get_media_container() skips empty 54px slivers (scrolled-past remnants) and returns
  the first candidate that actually describes a real post.
"""
from unittest.mock import MagicMock, patch

import pytest

from InstaAddict.core.views import PostsViewList


def _make_pvl():
    """Create a PostsViewList with a mocked device."""
    device = MagicMock()
    return PostsViewList(device)


class TestDescribesAPost:
    """Unit tests for _describes_a_post() helper."""

    def test_returns_outer_desc_when_present(self):
        """If media.get_desc() returns a non-empty string, use it directly."""
        pvl = _make_pvl()
        media = MagicMock()
        media.get_desc.return_value = "Photo by user, 50 likes"

        result = pvl._describes_a_post(media)

        assert result == "Photo by user, 50 likes"
        media.child.assert_not_called()

    def test_falls_back_to_inner_child_desc(self):
        """If outer is empty/None, check the inner ROW_FEED_PHOTO_IMAGEVIEW child."""
        pvl = _make_pvl()
        media = MagicMock()
        media.get_desc.return_value = None

        inner = MagicMock()
        inner.exists.return_value = True
        inner.get_desc.return_value = "Photo 1 of 3 by user"
        media.child.return_value = inner

        result = pvl._describes_a_post(media)

        assert result == "Photo 1 of 3 by user"
        media.child.assert_called_once()

    def test_returns_none_when_no_desc_anywhere(self):
        """If neither outer nor inner has a description, return None."""
        pvl = _make_pvl()
        media = MagicMock()
        media.get_desc.return_value = None

        inner = MagicMock()
        inner.exists.return_value = False
        media.child.return_value = inner

        result = pvl._describes_a_post(media)

        assert result is None

    def test_returns_none_when_inner_exists_but_empty(self):
        """Inner child exists but has empty desc -> return None."""
        pvl = _make_pvl()
        media = MagicMock()
        media.get_desc.return_value = ""  # empty string is falsy

        inner = MagicMock()
        inner.exists.return_value = True
        inner.get_desc.return_value = ""
        media.child.return_value = inner

        result = pvl._describes_a_post(media)

        assert result is None


class TestGetMediaContainer:
    """Unit tests for _get_media_container() sliver-skip logic."""

    def test_returns_none_when_no_media_exists(self):
        """When the media find returns nothing, return (media, None)."""
        pvl = _make_pvl()
        media_mock = MagicMock()
        media_mock.exists.return_value = False
        pvl.device.find.return_value = media_mock

        media, content_desc = pvl._get_media_container()

        assert media is media_mock
        assert content_desc is None

    def test_skips_empty_slivers_and_returns_described_candidate(self):
        """First candidate is an empty sliver; second has a description -> return second."""
        pvl = _make_pvl()

        # Initial find returns a collection of 2 items
        collection = MagicMock()
        collection.exists.return_value = True
        collection.count_items.return_value = 2
        pvl.device.find.return_value = collection

        # Candidate 0: sliver (no description anywhere)
        sliver = MagicMock()
        sliver.get_desc.return_value = None
        inner_sliver = MagicMock()
        inner_sliver.exists.return_value = False
        sliver.child.return_value = inner_sliver

        # Candidate 1: real post with description
        real_post = MagicMock()
        real_post.get_desc.return_value = "Photo by user, 100 likes"

        # pvl.device.find is called once for collection, then once per index
        pvl.device.find.side_effect = [collection, sliver, real_post]

        media, content_desc = pvl._get_media_container()

        assert media is real_post
        assert content_desc == "Photo by user, 100 likes"

    def test_returns_first_media_and_none_when_all_slivers(self):
        """All candidates are slivers (no description) -> return (first_media, None)."""
        pvl = _make_pvl()

        collection = MagicMock()
        collection.exists.return_value = True
        collection.count_items.return_value = 2

        sliver1 = MagicMock()
        sliver1.get_desc.return_value = None
        inner1 = MagicMock()
        inner1.exists.return_value = False
        sliver1.child.return_value = inner1

        sliver2 = MagicMock()
        sliver2.get_desc.return_value = None
        inner2 = MagicMock()
        inner2.exists.return_value = False
        sliver2.child.return_value = inner2

        pvl.device.find.side_effect = [collection, sliver1, sliver2]

        media, content_desc = pvl._get_media_container()

        assert content_desc is None
        assert media is collection  # returns original collection as fallback

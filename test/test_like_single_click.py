"""
Tests for PostsViewList._get_like_button_of() -- E3 upstream cherry-pick.

Verifies that the geometric like-button pairing selects the heart belonging to the
*current* post and not the post scrolled past above it. Covers JsonRpcError resilience.
"""
from unittest.mock import MagicMock

import pytest

from InstaAddict.core.device_facade import DeviceFacade
from InstaAddict.core.views import PostsViewList


def _make_pvl():
    """Create a PostsViewList with a mocked device."""
    device = MagicMock()
    return PostsViewList(device)


def _make_button(top: int) -> MagicMock:
    """Create a mock button with a known top bound."""
    btn = MagicMock()
    btn.get_bounds.return_value = {"top": top, "bottom": top + 48}
    return btn


class TestGetLikeButtonOf:
    """Unit tests for _get_like_button_of() geometric pairing."""

    def test_returns_none_when_no_buttons_exist(self):
        """If no ROW_FEED_BUTTON_LIKE buttons are present, return None."""
        pvl = _make_pvl()
        buttons = MagicMock()
        buttons.exists.return_value = False
        pvl.device.find.return_value = buttons

        media = MagicMock()
        media.get_bounds.return_value = {"bottom": 400}

        result = pvl._get_like_button_of(media)

        assert result is None

    def test_picks_button_below_media(self):
        """Two buttons: one above media_bottom, one below -> selects the one below."""
        pvl = _make_pvl()

        # media_bottom = 400
        media = MagicMock()
        media.get_bounds.return_value = {"bottom": 400}

        # Buttons collection
        buttons_collection = MagicMock()
        buttons_collection.exists.return_value = True
        buttons_collection.count_items.return_value = 2

        btn_above = _make_button(top=100)   # above media (100 < 400) -- must skip
        btn_below = _make_button(top=520)   # below media (520 >= 400) -- must pick

        pvl.device.find.side_effect = [
            buttons_collection,  # initial find
            btn_above,           # index=0
            btn_below,           # index=1
        ]

        result = pvl._get_like_button_of(media)

        assert result is btn_below

    def test_picks_closest_button_when_multiple_below(self):
        """Three buttons below media: picks the one with the smallest top value."""
        pvl = _make_pvl()

        media = MagicMock()
        media.get_bounds.return_value = {"bottom": 300}

        buttons_collection = MagicMock()
        buttons_collection.exists.return_value = True
        buttons_collection.count_items.return_value = 3

        btn_first = _make_button(top=500)   # closest below (500 >= 300) -- pick
        btn_second = _make_button(top=520)
        btn_third = _make_button(top=600)

        pvl.device.find.side_effect = [
            buttons_collection,
            btn_first,
            btn_second,
            btn_third,
        ]

        result = pvl._get_like_button_of(media)

        assert result is btn_first

    def test_media_bounds_jsonrpc_error_falls_back_to_zero(self):
        """If media.get_bounds() raises JsonRpcError, media_bottom=0 is used.

        With media_bottom=0, all buttons have top >= 0 so the one with the smallest
        top is selected (closest to top of screen when no geometric anchor is available).
        """
        pvl = _make_pvl()

        media = MagicMock()
        media.get_bounds.side_effect = DeviceFacade.JsonRpcError("rpc failed", None)

        buttons_collection = MagicMock()
        buttons_collection.exists.return_value = True
        buttons_collection.count_items.return_value = 2

        btn_a = _make_button(top=200)  # top=200 >= 0, closer
        btn_b = _make_button(top=500)  # top=500 >= 0, farther

        pvl.device.find.side_effect = [
            buttons_collection,
            btn_a,
            btn_b,
        ]

        result = pvl._get_like_button_of(media)

        # With media_bottom=0, btn_a (top=200) is picked as closest >= 0
        assert result is btn_a

    def test_candidate_bounds_jsonrpc_error_is_skipped(self):
        """If a candidate button.get_bounds() raises JsonRpcError, skip it."""
        pvl = _make_pvl()

        media = MagicMock()
        media.get_bounds.return_value = {"bottom": 400}

        buttons_collection = MagicMock()
        buttons_collection.exists.return_value = True
        buttons_collection.count_items.return_value = 2

        # btn_bad raises on get_bounds -> should be skipped
        btn_bad = MagicMock()
        btn_bad.get_bounds.side_effect = DeviceFacade.JsonRpcError("rpc failed", None)

        btn_good = _make_button(top=500)

        pvl.device.find.side_effect = [
            buttons_collection,
            btn_bad,
            btn_good,
        ]

        result = pvl._get_like_button_of(media)

        assert result is btn_good

import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from InstaAddict.plugins.upload_posts import UploadPostsPlugin


@pytest.fixture
def plugin():
    return UploadPostsPlugin()


@pytest.fixture
def temp_images(tmp_path):
    """Generates temporary test images with known aspect ratios."""
    # 1. Landscape image (1200 x 800 -> ratio 1.50)
    landscape_path = str(tmp_path / "landscape.jpg")
    img_landscape = Image.new("RGB", (1200, 800), color="blue")
    img_landscape.save(landscape_path, "JPEG")

    # 2. Portrait image (800 x 1200 -> ratio 0.67)
    portrait_path = str(tmp_path / "portrait.jpg")
    img_portrait = Image.new("RGB", (800, 1200), color="green")
    img_portrait.save(portrait_path, "JPEG")

    # 3. Square image (1000 x 1000 -> ratio 1.00)
    square_path = str(tmp_path / "square.jpg")
    img_square = Image.new("RGB", (1000, 1000), color="red")
    img_square.save(square_path, "JPEG")

    return {
        "landscape": landscape_path,
        "portrait": portrait_path,
        "square": square_path,
    }


def test_upload_force_square_argument_registered(plugin):
    """Verifies that --upload-force-square argument is properly registered."""
    arg_names = [arg["arg"] for arg in plugin.arguments]
    assert "--upload-force-square" in arg_names
    force_square_arg = next(
        a for a in plugin.arguments if a["arg"] == "--upload-force-square"
    )
    assert force_square_arg["action"] == "store_true"


def test_detect_media_aspect_ratio_landscape(plugin, temp_images):
    """Detects landscape aspect ratio for wide media."""
    result = plugin._detect_media_aspect_ratio(temp_images["landscape"])
    assert result == "landscape"


def test_detect_media_aspect_ratio_portrait(plugin, temp_images):
    """Detects portrait aspect ratio for tall media."""
    result = plugin._detect_media_aspect_ratio(temp_images["portrait"])
    assert result == "portrait"


def test_detect_media_aspect_ratio_square(plugin, temp_images):
    """Detects square aspect ratio for 1:1 media."""
    result = plugin._detect_media_aspect_ratio(temp_images["square"])
    assert result == "square"


def test_detect_media_aspect_ratio_nonexistent(plugin):
    """Returns square gracefully when file does not exist."""
    result = plugin._detect_media_aspect_ratio("nonexistent/path/media.jpg")
    assert result == "square"


def test_detect_media_aspect_ratio_corrupt(plugin, tmp_path):
    """Returns square gracefully when file is corrupt or unreadable."""
    corrupt_path = str(tmp_path / "corrupt.jpg")
    with open(corrupt_path, "wb") as f:
        f.write(b"not a valid image")
    result = plugin._detect_media_aspect_ratio(corrupt_path)
    assert result == "square"


def test_adjust_aspect_ratio_square_noop(plugin):
    """Square form factor requires no adjustment and returns True immediately."""
    device = MagicMock()
    result = plugin._adjust_aspect_ratio(device, "square")
    assert result is True
    device.deviceV2.assert_not_called()


def test_adjust_aspect_ratio_modern_landscape_success(plugin):
    """Modern Instagram v446+ selects Ratio tool -> Landscape -> Done."""
    device = MagicMock()
    d = MagicMock()
    device.deviceV2 = d
    device.app_id = "com.instagram.android"

    ratio_btn = MagicMock()
    ratio_btn.exists.return_value = True

    landscape_opt = MagicMock()
    landscape_opt.exists.return_value = True

    done_btn = MagicMock()
    done_btn.exists.return_value = True

    def mock_d_call(**kwargs):
        if "Ratio" in str(kwargs.get("textMatches", "")) or "Ratio" in str(
            kwargs.get("descriptionMatches", "")
        ):
            return ratio_btn
        if "Landscape" in str(kwargs.get("textMatches", "")) or "Landscape" in str(
            kwargs.get("descriptionMatches", "")
        ):
            return landscape_opt
        if "bottom_sheet_done_button" in str(
            kwargs.get("resourceId", "")
        ) or "Done" in str(kwargs.get("textMatches", "")):
            return done_btn
        mock_fallback = MagicMock()
        mock_fallback.exists.return_value = False
        return mock_fallback

    d.side_effect = mock_d_call

    with patch("InstaAddict.plugins.upload_posts.random_sleep"):
        result = plugin._adjust_aspect_ratio(device, "landscape")

    assert result is True
    ratio_btn.click.assert_called_once()
    landscape_opt.click.assert_called_once()
    done_btn.click.assert_called_once()


def test_adjust_aspect_ratio_modern_portrait_success(plugin):
    """Modern Instagram v446+ selects Ratio tool -> Portrait -> Done."""
    device = MagicMock()
    d = MagicMock()
    device.deviceV2 = d
    device.app_id = "com.instagram.android"

    ratio_btn = MagicMock()
    ratio_btn.exists.return_value = True

    portrait_opt = MagicMock()
    portrait_opt.exists.return_value = True

    done_btn = MagicMock()
    done_btn.exists.return_value = True

    def mock_d_call(**kwargs):
        if "Ratio" in str(kwargs.get("textMatches", "")) or "Ratio" in str(
            kwargs.get("descriptionMatches", "")
        ):
            return ratio_btn
        if "Portrait" in str(kwargs.get("textMatches", "")) or "Portrait" in str(
            kwargs.get("descriptionMatches", "")
        ):
            return portrait_opt
        if "bottom_sheet_done_button" in str(
            kwargs.get("resourceId", "")
        ) or "Done" in str(kwargs.get("textMatches", "")):
            return done_btn
        mock_fallback = MagicMock()
        mock_fallback.exists.return_value = False
        return mock_fallback

    d.side_effect = mock_d_call

    with patch("InstaAddict.plugins.upload_posts.random_sleep"):
        result = plugin._adjust_aspect_ratio(device, "portrait")

    assert result is True
    ratio_btn.click.assert_called_once()
    portrait_opt.click.assert_called_once()
    done_btn.click.assert_called_once()


def test_adjust_aspect_ratio_classic_cropper_toggle_fallback(plugin):
    """Falls back to classic cropper_toggle_button when Ratio tool is not present."""
    device = MagicMock()
    d = MagicMock()
    device.deviceV2 = d
    device.app_id = "com.instagram.android"

    cropper_btn = MagicMock()
    cropper_btn.exists.return_value = True

    def mock_d_call(**kwargs):
        if "cropper_toggle_button" in str(
            kwargs.get("resourceId", "")
        ) or "cropper_toggle_button" in str(kwargs.get("resourceIdMatches", "")):
            return cropper_btn
        mock_fallback = MagicMock()
        mock_fallback.exists.return_value = False
        return mock_fallback

    d.side_effect = mock_d_call

    with patch("InstaAddict.plugins.upload_posts.random_sleep"):
        result = plugin._adjust_aspect_ratio(device, "landscape")

    assert result is True
    cropper_btn.click.assert_called_once()


def test_adjust_aspect_ratio_no_controls_graceful_fallback(plugin):
    """Gracefully returns False without crashing when no aspect ratio controls exist."""
    device = MagicMock()
    d = MagicMock()
    device.deviceV2 = d
    device.app_id = "com.instagram.android"

    mock_none = MagicMock()
    mock_none.exists.return_value = False
    d.side_effect = lambda **kwargs: mock_none

    with patch("InstaAddict.plugins.upload_posts.random_sleep"):
        result = plugin._adjust_aspect_ratio(device, "landscape")

    assert result is False


def test_upload_to_ig_respects_force_square(plugin, temp_images):
    """Verifies that _upload_to_ig with force_square=True skips aspect ratio adjustment."""
    device = MagicMock()
    device.deviceV2.serial = "emulator-5554"
    d = device.deviceV2

    plugin._execute_adb = MagicMock(return_value=True)
    plugin._get_mediastore_id = MagicMock(return_value="100")
    plugin._adjust_aspect_ratio = MagicMock()

    caption_input = MagicMock()
    caption_input.exists.return_value = True
    share_footer = MagicMock()
    share_footer.exists.return_value = True

    d.side_effect = lambda **kwargs: caption_input

    with patch("InstaAddict.plugins.upload_posts.random_sleep"):
        plugin._upload_to_ig(
            device,
            temp_images["landscape"],
            "Test caption",
            force_square=True,
        )

    # _adjust_aspect_ratio should NOT have been called
    plugin._adjust_aspect_ratio.assert_not_called()


def test_upload_to_ig_executes_aspect_ratio_adjustment(plugin, temp_images):
    """Verifies that _upload_to_ig with force_square=False calls _adjust_aspect_ratio."""
    device = MagicMock()
    device.deviceV2.serial = "emulator-5554"
    d = device.deviceV2

    plugin._execute_adb = MagicMock(return_value=True)
    plugin._get_mediastore_id = MagicMock(return_value="100")
    plugin._adjust_aspect_ratio = MagicMock(return_value=True)

    caption_input = MagicMock()
    caption_input.exists.return_value = True
    share_footer = MagicMock()
    share_footer.exists.return_value = True

    d.side_effect = lambda **kwargs: caption_input

    with patch("InstaAddict.plugins.upload_posts.random_sleep"):
        plugin._upload_to_ig(
            device,
            temp_images["landscape"],
            "Test caption",
            force_square=False,
        )

    # _adjust_aspect_ratio should have been called with 'landscape'
    plugin._adjust_aspect_ratio.assert_called_once_with(device, "landscape")

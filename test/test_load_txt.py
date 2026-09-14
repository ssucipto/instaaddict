import os
from InstaAddict.core.interaction import _load_and_clean_txt_file


def test_load_txt_ok(mocker):
    target_path = os.path.join(os.path.dirname(__file__), "txt", "txt_ok.txt")
    mocker.patch("os.path.join", return_value=target_path)
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is not None
    assert message == [
        "Hello, test_user! How are you today?",
        "Hello everyone!",
        "Goodbye, test_user! Have a great day!",
    ]


def test_load_txt_empty(mocker):
    target_path = os.path.join(os.path.dirname(__file__), "txt", "txt_empty.txt")
    mocker.patch("os.path.join", return_value=target_path)
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is None


def test_load_txt_not_exists(mocker):
    target_path = os.path.join(os.path.dirname(__file__), "txt", "txt_not_exists.txt")
    mocker.patch("os.path.join", return_value=target_path)
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is None


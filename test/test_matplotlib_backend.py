import os
import sys
import threading
from unittest.mock import MagicMock, patch


def test_matplotlib_backend_is_agg():
    """Verify that importing DataAnalytics enforces the non-GUI Agg backend."""
    import matplotlib
    from InstaAddict.plugins.data_analytics import DataAnalytics

    assert DataAnalytics is not None
    assert matplotlib.get_backend().lower() == "agg"


def test_tkinter_never_loaded_on_import():
    """Verify that neither tkinter nor _tkinter are loaded into sys.modules."""
    from InstaAddict.plugins.data_analytics import DataAnalytics
    assert DataAnalytics is not None

    assert "tkinter" not in sys.modules
    assert "_tkinter" not in sys.modules


def test_figure_creation_does_not_load_tkinter():
    """Verify that creating subplots and rendering figures does not load Tkinter."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(ncols=1, nrows=1)
    ax.plot([1, 2, 3], [4, 5, 6])
    plt.close(fig)

    assert "tkinter" not in sys.modules
    assert "_tkinter" not in sys.modules


def test_data_analytics_report_generation_under_agg(tmp_path):
    """Verify that DataAnalytics can generate a PDF report cleanly using the Agg backend."""
    from InstaAddict.plugins.data_analytics import DataAnalytics

    plugin = DataAnalytics()
    plugin.username = "test_user"

    mock_storage = MagicMock()
    mock_storage.report_path = str(tmp_path / "reports")

    mock_device = MagicMock()
    mock_configs = MagicMock()
    mock_configs.args = MagicMock()

    mock_session = {
        "profile": {"followers": 100},
        "start_time": "2026-09-18 10:00:00.000000",
        "finish_time": "2026-09-18 10:10:00.000000",
        "total_followed": 5,
        "total_unfollowed": 2,
        "total_likes": 10,
        "successful_interactions": 3,
        "args": {"likes_count": 2, "follow_percentage": 50},
        "my_username": "test_user",
    }

    mock_session_state = MagicMock()
    mock_session_state.my_username = "test_user"

    with patch.object(plugin, "load_sessions", return_value=[mock_session]):
        plugin.run(mock_device, mock_configs, mock_storage, [mock_session_state], plugin)

    # PDF and MD reports should be generated
    files = os.listdir(mock_storage.report_path)
    assert any(f.endswith(".pdf") for f in files)
    assert any(f.endswith(".md") for f in files)
    assert "tkinter" not in sys.modules


def test_multithreaded_teardown_safety():
    """Verify that spawning and terminating background threads alongside plotting does not raise Tcl_AsyncDelete."""
    import matplotlib.pyplot as plt

    errors = []

    def worker():
        try:
            fig, ax = plt.subplots(ncols=1, nrows=1)
            ax.bar(["a", "b"], [1, 2])
            plt.close(fig)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3.0)

    assert len(errors) == 0
    assert "tkinter" not in sys.modules


def test_matplotlib_missing_graceful_handling():
    """Verify that if matplotlib is missing, DataAnalytics logs an error without crashing."""
    from InstaAddict.plugins.data_analytics import DataAnalytics
    import InstaAddict.plugins.data_analytics as da_module

    plugin = DataAnalytics()
    orig_available = da_module.MATPLOTLIB_AVAILABLE
    try:
        da_module.MATPLOTLIB_AVAILABLE = False
        with patch.object(da_module.logger, "error") as mock_err:
            plugin.run(MagicMock(), MagicMock(), MagicMock(), [MagicMock()], plugin)
            assert mock_err.called
            assert "Matplotlib is required" in mock_err.call_args[0][0]
    finally:
        da_module.MATPLOTLIB_AVAILABLE = orig_available

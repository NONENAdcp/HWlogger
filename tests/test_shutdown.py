import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from hwlogger.services.config_service import AppConfig, ConfigService
from hwlogger.ui.main_window import MainWindow


def _window(tmp_path, monkeypatch, qtbot):
    monkeypatch.setenv("HWLOGGER_FAKE_SENSORS", "1")
    config = AppConfig(log_directory=str(tmp_path / "logs"), ui_interval_ms=50)
    window = MainWindow(ConfigService(tmp_path / "config.json"), config)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: bool(window.latest_values), timeout=2000)
    return window


def test_shutdown_without_recording_is_bounded(tmp_path, monkeypatch, qtbot):
    window = _window(tmp_path, monkeypatch, qtbot)
    for index in range(3):
        window.graphs_tab.selector.item(index).setCheckState(
            Qt.CheckState.Checked
        )
    started = time.perf_counter()
    window.close()
    elapsed = time.perf_counter() - started
    assert elapsed < 1.0
    assert not window.polling.thread.isRunning()


def test_shutdown_during_recording_preserves_session(tmp_path, monkeypatch, qtbot):
    window = _window(tmp_path, monkeypatch, qtbot)
    window.sensors[0].selected_for_log = True
    window.start_recording()
    window._log_row()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    started = time.perf_counter()
    window.close()
    elapsed = time.perf_counter() - started
    assert elapsed < 1.0
    assert not window.polling.thread.isRunning()
    assert len(list((tmp_path / "logs").glob("hwlog_*.csv"))) == 2
    assert len(list((tmp_path / "logs").glob("hwlog_*.json"))) == 1

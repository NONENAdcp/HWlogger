from __future__ import annotations

import json
from unittest.mock import Mock

from PySide6.QtCore import QRect, Qt

from hwlogger.backends.fake import FakeSensorBackend
from hwlogger.services.config_service import (
    DEFAULT_UI_INTERVAL_MS,
    AppConfig,
    ConfigService,
)
from hwlogger.ui.graphs_tab import GraphsTab
from hwlogger.ui.main_window import MainWindow


def _window(tmp_path, monkeypatch, qtbot, config=None):
    monkeypatch.setenv("HWLOGGER_FAKE_SENSORS", "1")
    service = ConfigService(tmp_path / "config.json")
    window = MainWindow(
        service,
        config or AppConfig(log_directory=str(tmp_path / "logs")),
        tray_available=False,
    )
    qtbot.addWidget(window)
    window.show()
    return window, service


def _screen_intersects_title(window) -> bool:
    frame = window.frameGeometry()
    title = QRect(frame.x(), frame.y(), max(120, frame.width()), 40)
    return any(
        screen.availableGeometry().intersects(title)
        for screen in window.screen().virtualSiblings()
    )


def _set_graph_checked(tab: GraphsTab, sensor_id: str, checked: bool) -> None:
    for index in range(tab.selector.count()):
        item = tab.selector.item(index)
        if item.data(Qt.ItemDataRole.UserRole) == sensor_id:
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            return
    raise AssertionError(f"missing graph selector item: {sensor_id}")


def test_window_geometry_and_active_tab_roundtrip(tmp_path, monkeypatch, qtbot):
    first, service = _window(tmp_path, monkeypatch, qtbot)
    first.resize(700, 500)
    first.move(30, 40)
    first.tabs.setCurrentIndex(2)
    expected_size = first.size()
    first.request_exit()
    saved = service.load()
    assert saved.window_geometry
    assert saved.active_tab == "logs"

    second = MainWindow(service, saved, tray_available=False)
    qtbot.addWidget(second)
    second.show()
    assert second.size() == expected_size
    assert second.tabs.currentIndex() == 2
    assert _screen_intersects_title(second)
    second.request_exit()


def test_maximized_restores_but_minimized_does_not(tmp_path, monkeypatch, qtbot):
    maximized, service = _window(tmp_path / "max", monkeypatch, qtbot)
    maximized.showMaximized()
    qtbot.wait(20)
    maximized.request_exit()
    saved = service.load()
    assert saved.window_maximized
    restored = MainWindow(service, saved, tray_available=False)
    qtbot.addWidget(restored)
    restored.show()
    assert restored.isMaximized()
    restored.request_exit()

    minimized, min_service = _window(tmp_path / "min", monkeypatch, qtbot)
    minimized.showMinimized()
    qtbot.wait(20)
    minimized.request_exit()
    restored_min = MainWindow(
        min_service, min_service.load(), tray_available=False
    )
    qtbot.addWidget(restored_min)
    restored_min.show()
    assert not restored_min.isMinimized()
    restored_min.request_exit()


def test_invalid_and_offscreen_geometry_falls_back_safely(
    tmp_path, monkeypatch, qtbot
):
    invalid = AppConfig(
        log_directory=str(tmp_path / "invalid-logs"),
        window_geometry="not base64!",
    )
    window, _service = _window(tmp_path / "invalid", monkeypatch, qtbot, invalid)
    assert _screen_intersects_title(window)
    window.request_exit()

    offscreen, service = _window(tmp_path / "offscreen", monkeypatch, qtbot)
    offscreen.move(50_000, 50_000)
    offscreen.request_exit()
    restored = MainWindow(service, service.load(), tray_available=False)
    qtbot.addWidget(restored)
    restored.show()
    assert _screen_intersects_title(restored)
    restored.request_exit()


def test_invalid_tab_and_polling_interval_use_defaults(
    tmp_path, monkeypatch, qtbot
):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "active_tab": "removed-tab",
                "ui_interval_ms": -50,
                "log_directory": str(tmp_path / "logs"),
            }
        ),
        encoding="utf-8",
    )
    service = ConfigService(path)
    config = service.load()
    assert config.active_tab == "sensors"
    assert config.ui_interval_ms == DEFAULT_UI_INTERVAL_MS
    monkeypatch.setenv("HWLOGGER_FAKE_SENSORS", "1")
    window = MainWindow(service, config, tray_available=False)
    qtbot.addWidget(window)
    assert window.tabs.currentIndex() == 0
    assert window.polling.worker.interval_ms == DEFAULT_UI_INTERVAL_MS
    window.request_exit()


def test_polling_interval_change_is_saved_for_next_start(
    tmp_path, monkeypatch, qtbot
):
    window, service = _window(tmp_path, monkeypatch, qtbot)
    original_worker_interval = window.polling.worker.interval_ms
    window.settings_tab.ui_interval.setValue(250)
    assert service.load().ui_interval_ms == 250
    assert window.polling.worker.interval_ms == original_worker_interval
    window.request_exit()
    restarted = MainWindow(service, service.load(), tray_available=False)
    qtbot.addWidget(restarted)
    assert restarted.polling.worker.interval_ms == 250
    restarted.request_exit()


def test_graph_selection_restores_order_without_history(
    tmp_path, monkeypatch, qtbot
):
    selected = ["fake:frequency", "fake:temperature", "missing:sensor"]
    config = AppConfig(
        log_directory=str(tmp_path / "logs"),
        selected_graph_sensors=selected,
    )
    first, service = _window(tmp_path, monkeypatch, qtbot, config)
    assert first.graphs_tab._selected_ids() == selected[:2]
    first.graphs_tab.update_values(
        {"fake:frequency": 2000.0, "fake:temperature": 50.0}
    )
    assert first.graphs_tab.graph.series["fake:frequency"].values
    first.request_exit()

    second = MainWindow(service, service.load(), tray_available=False)
    qtbot.addWidget(second)
    assert second.graphs_tab._selected_ids() == selected[:2]
    assert not second.graphs_tab.graph.series["fake:frequency"].values
    assert "missing:sensor" not in second.graphs_tab.graph.series
    second.request_exit()


def test_graph_selection_updates_config_and_empty_stays_empty(
    tmp_path, monkeypatch, qtbot
):
    window, service = _window(tmp_path, monkeypatch, qtbot)
    _set_graph_checked(window.graphs_tab, "fake:temperature", True)
    _set_graph_checked(window.graphs_tab, "fake:frequency", True)
    assert service.load().selected_graph_sensors == [
        "fake:temperature",
        "fake:frequency",
    ]
    _set_graph_checked(window.graphs_tab, "fake:temperature", False)
    _set_graph_checked(window.graphs_tab, "fake:frequency", False)
    assert service.load().selected_graph_sensors == []
    window.request_exit()


def test_missing_graph_sensor_returns_on_rescan_without_duplicates(qtbot):
    sensors = FakeSensorBackend().scan()
    late = sensors[0]
    available = sensors[1]
    tab = GraphsTab(
        selected_sensor_ids=[late.sensor_id, available.sensor_id]
    )
    qtbot.addWidget(tab)
    tab.set_sensors([available])
    assert tab._selected_ids() == [available.sensor_id]
    assert list(tab.graph.series) == [available.sensor_id]
    tab.set_sensors([late, available])
    assert tab._selected_ids() == [late.sensor_id, available.sensor_id]
    assert set(tab.graph.series) == {late.sensor_id, available.sensor_id}
    tab.set_sensors([late, available])
    assert len(tab.graph.series) == 2


def test_graph_restore_respects_eight_line_limit(qtbot):
    sensors = FakeSensorBackend().scan()
    expanded = []
    for index in range(10):
        sensor = sensors[index % len(sensors)]
        sensor = sensor.__class__(
            sensor_id=f"sensor:{index}",
            name=f"Sensor {index}",
            original_name=sensor.original_name,
            source=sensor.source,
            category=sensor.category,
            sensor_type=sensor.sensor_type,
            unit=sensor.unit,
            backend_id=f"sensor:{index}",
            reader=sensor.reader,
        )
        expanded.append(sensor)
    tab = GraphsTab(selected_sensor_ids=[sensor.sensor_id for sensor in expanded])
    qtbot.addWidget(tab)
    tab.set_sensors(expanded)
    assert len(tab._selected_ids()) == 8
    assert len(tab.graph.series) == 8


def test_old_and_partially_invalid_config_preserves_valid_fields(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "log_directory": "/tmp/kept",
                "close_to_tray": False,
                "ui_interval_ms": "broken",
                "window_geometry": 123,
                "selected_graph_sensors": ["one", 2],
            }
        ),
        encoding="utf-8",
    )
    config = ConfigService(path).load()
    assert config.log_directory == "/tmp/kept"
    assert not config.close_to_tray
    assert config.ui_interval_ms == DEFAULT_UI_INTERVAL_MS
    assert config.window_geometry == ""
    assert config.selected_graph_sensors == []

    old_path = tmp_path / "old.json"
    old_path.write_text(
        json.dumps({"log_directory": "/tmp/old", "window_width": 900}),
        encoding="utf-8",
    )
    old = ConfigService(old_path).load()
    assert old.log_directory == "/tmp/old"
    assert old.window_width == 900
    assert old.active_tab == "sensors"


def test_close_to_tray_survives_unavailable_tray_and_shutdown_is_idempotent(
    tmp_path, monkeypatch, qtbot
):
    window, service = _window(
        tmp_path,
        monkeypatch,
        qtbot,
        AppConfig(
            log_directory=str(tmp_path / "logs"),
            close_to_tray=True,
        ),
    )
    save = Mock(wraps=service.save)
    monkeypatch.setattr(service, "save", save)
    assert not window.settings_tab.close_to_tray.isEnabled()
    window.request_exit()
    window.request_exit()
    assert service.load().close_to_tray
    assert save.call_count == 1

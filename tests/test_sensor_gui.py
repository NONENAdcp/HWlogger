from __future__ import annotations

from PySide6.QtCore import Qt

from hwlogger.backends.fake import FakeSensorBackend
from hwlogger.models.sensor import Sensor, SensorCategory, SensorType
from hwlogger.services.config_service import AppConfig
from hwlogger.services.polling_service import PollingService
from hwlogger.services.sensor_manager import SensorManager
from hwlogger.ui.sensors_tab import SensorsTab
from hwlogger.widgets.sensor_table import SensorTable


def _many_sensors(count: int) -> list[Sensor]:
    return [
        Sensor(
            sensor_id=f"scroll:{index}",
            name=f"Sensor {index}",
            original_name=f"sensor{index}_input",
            source="test",
            category=SensorCategory.OTHER,
            sensor_type=SensorType.TEMPERATURE,
            unit="°C",
            backend_id=f"/test/sensor{index}",
            reader=lambda index=index: float(index),
            value=float(index),
        )
        for index in range(count)
    ]


def test_polling_signal_changes_table_model_and_emits_data_changed(qtbot, monkeypatch):
    monkeypatch.setenv("HWLOGGER_FAKE_SENSORS", "1")
    manager = SensorManager(AppConfig())
    sensors = manager.scan()
    tab = SensorsTab()
    qtbot.addWidget(tab)
    tab.set_sensors(sensors)
    tab.show()
    polling = PollingService(manager, 50)
    polling.values_ready.connect(lambda _values: tab.update_values())
    model_changes: list[tuple] = []
    tab.table.model().dataChanged.connect(
        lambda top_left, bottom_right, roles: model_changes.append(
            (top_left.row(), bottom_right.row(), roles)
        )
    )
    first_item = tab.table.item(0, 5)
    assert first_item.text() == "—"
    try:
        polling.start()
        qtbot.waitUntil(lambda: first_item.text() != "—", timeout=2000)
        assert model_changes
        assert sensors[0].value is not None
    finally:
        polling.stop()
        manager.shutdown()


def test_table_has_working_vertical_scrollbar_for_more_than_60_rows(qtbot):
    table = SensorTable()
    qtbot.addWidget(table)
    table.resize(900, 320)
    table.set_sensors(_many_sensors(80), decimals=2)
    table.show()
    qtbot.waitUntil(lambda: table.verticalScrollBar().maximum() > 0)
    scrollbar = table.verticalScrollBar()
    assert table.rowCount() == 80
    assert scrollbar.maximum() > 0
    scrollbar.setValue(scrollbar.maximum())
    qtbot.wait(20)
    last_item = table.item(table.rowCount() - 1, 1)
    assert table.visualItemRect(last_item).intersects(table.viewport().rect())
    assert table.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def test_fake_backend_values_change_over_time(qtbot):
    backend = FakeSensorBackend()
    sensors = backend.scan()
    first = [sensor.read() for sensor in sensors]
    qtbot.wait(1100)
    second = [sensor.read() for sensor in sensors]
    assert first != second

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


def test_compact_table_hides_technical_columns_and_embeds_units(qtbot):
    sensors = _many_sensors(2)
    sensors[0].value = 48.0
    tab = SensorsTab()
    qtbot.addWidget(tab)
    tab.set_sensors(sensors, decimals=0)
    visible_headers = [
        tab.table.horizontalHeaderItem(column).text()
        for column in range(tab.table.columnCount())
        if not tab.table.isColumnHidden(column)
    ]
    assert visible_headers == [
        "Запись",
        "Имя",
        "Сейчас",
        "Минимум",
        "Среднее",
        "Максимум",
        "Состояние",
    ]
    assert tab.table.item(0, 5).text() == "48 °C"
    tab.technical_columns.setChecked(True)
    assert not tab.table.isColumnHidden(2)


def test_sensor_column_widths_roundtrip(qtbot):
    table = SensorTable()
    qtbot.addWidget(table)
    table.setColumnWidth(5, 147)
    widths = table.column_widths()
    restored = SensorTable()
    qtbot.addWidget(restored)
    restored.restore_column_widths(widths)
    assert restored.columnWidth(5) == 147


def test_fake_backend_values_change_over_time(qtbot):
    backend = FakeSensorBackend()
    sensors = backend.scan()
    first = [sensor.read() for sensor in sensors]
    qtbot.wait(1100)
    second = [sensor.read() for sensor in sensors]
    assert first != second


def _brush_is_standard(item) -> bool:
    return item.background().style() == Qt.BrushStyle.NoBrush


def test_temperature_styles_only_current_and_maximum(qtbot):
    sensor = _many_sensors(1)[0]
    sensor.value = 90.0
    sensor.statistics.add(95.0)
    table = SensorTable()
    qtbot.addWidget(table)
    table.set_sensors([sensor])

    assert not _brush_is_standard(table.item(0, 5))
    assert table.item(0, 5).font().bold()
    assert not _brush_is_standard(table.item(0, 8))
    assert table.item(0, 8).font().bold()
    assert _brush_is_standard(table.item(0, 6))
    assert _brush_is_standard(table.item(0, 7))
    assert _brush_is_standard(table.item(0, 1))
    assert _brush_is_standard(table.item(0, 9))


def test_temperature_current_and_maximum_have_independent_hysteresis(qtbot):
    sensor = _many_sensors(1)[0]
    sensor.value = 80.0
    sensor.statistics.maximum = 90.0
    table = SensorTable()
    qtbot.addWidget(table)
    table.set_sensors([sensor])

    sensor.value = 77.9
    sensor.statistics.maximum = 88.1
    table.update_sensor_values({sensor.sensor_id: sensor}, 0)

    current = table.item(0, 5)
    maximum = table.item(0, 8)
    assert current.background().color() != maximum.background().color()
    assert not current.font().bold()
    assert maximum.font().bold()


def test_non_temperature_sensor_is_not_colored_by_name_or_value(qtbot):
    sensor = _many_sensors(1)[0]
    sensor.name = "Температура CPU"
    sensor.sensor_type = SensorType.POWER
    sensor.unit = "W"
    sensor.value = 95.0
    sensor.statistics.add(95.0)
    table = SensorTable()
    qtbot.addWidget(table)
    table.set_sensors([sensor])

    assert _brush_is_standard(table.item(0, 5))
    assert _brush_is_standard(table.item(0, 8))


def test_temperature_style_resets_for_none_unavailable_and_set_sensors(qtbot):
    sensor = _many_sensors(1)[0]
    sensor.value = 95.0
    sensor.statistics.add(95.0)
    table = SensorTable()
    qtbot.addWidget(table)
    table.set_sensors([sensor])
    assert table.item(0, 5).font().bold()

    sensor.value = None
    table.update_sensor_values({sensor.sensor_id: sensor}, 0)
    assert _brush_is_standard(table.item(0, 5))
    assert not table.item(0, 5).font().bold()

    sensor.value = 95.0
    sensor.available = False
    table.update_sensor_values({sensor.sensor_id: sensor}, 0)
    assert _brush_is_standard(table.item(0, 5))
    assert _brush_is_standard(table.item(0, 8))

    sensor.available = True
    sensor.value = 69.9
    sensor.statistics.reset()
    sensor.statistics.add(69.9)
    table.set_sensors([sensor])
    assert _brush_is_standard(table.item(0, 5))
    assert _brush_is_standard(table.item(0, 8))
    assert not table.item(0, 5).font().bold()


def test_critical_temperature_colors_have_readable_contrast(qtbot):
    sensor = _many_sensors(1)[0]
    sensor.value = 95.0
    table = SensorTable()
    qtbot.addWidget(table)
    table.set_sensors([sensor])
    item = table.item(0, 5)

    background = item.background().color()
    foreground = item.foreground().color()
    assert background.isValid()
    assert foreground.isValid()
    assert background.lightness() < foreground.lightness()

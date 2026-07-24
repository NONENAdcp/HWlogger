from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hwlogger.models.sensor import Sensor, SensorCategory, SensorType
from hwlogger.widgets.sensor_table import SensorTable


class SensorsTab(QWidget):
    selection_changed = Signal()
    rescan_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.all_sensors: list[Sensor] = []
        self.decimals = 2
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск датчиков…")
        self.category = QComboBox()
        self.category.addItem("Все категории", None)
        for category in SensorCategory:
            self.category.addItem(category.value, category)
        self.kind = QComboBox()
        self.kind.addItem("Все типы", None)
        for kind in SensorType:
            self.kind.addItem(kind.value, kind)
        self.table = SensorTable()
        enable = QPushButton("Включить все видимые")
        disable = QPushButton("Отключить все видимые")
        reset = QPushButton("Сбросить статистику")
        rescan = QPushButton("Пересканировать")
        controls = QHBoxLayout()
        for widget in (self.search, self.category, self.kind, enable, disable, reset, rescan):
            controls.addWidget(widget)
        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.table)
        self.search.textChanged.connect(self.refresh)
        self.category.currentIndexChanged.connect(self.refresh)
        self.kind.currentIndexChanged.connect(self.refresh)
        self.table.selection_changed.connect(self._sync_selection)
        enable.clicked.connect(lambda: self._set_visible(True))
        disable.clicked.connect(lambda: self._set_visible(False))
        reset.clicked.connect(self._reset_stats)
        rescan.clicked.connect(self.rescan_requested)

    def set_sensors(self, sensors: list[Sensor], decimals: int = 2) -> None:
        self.all_sensors = sensors
        self.decimals = decimals
        self.refresh()

    def refresh(self) -> None:
        text = self.search.text().casefold()
        category = self.category.currentData()
        kind = self.kind.currentData()
        visible = [
            sensor
            for sensor in self.all_sensors
            if (
                not text
                or text
                in (
                    f"{sensor.name} {sensor.original_name} "
                    f"{sensor.source} {sensor.backend_id}"
                ).casefold()
            )
            and (category is None or sensor.category == category)
            and (kind is None or sensor.sensor_type == kind)
        ]
        self.table.set_sensors(visible, self.decimals)

    def update_values(self) -> int:
        """Update existing table rows without rebuilding or re-sorting the widget."""
        return self.table.update_sensor_values(
            {sensor.sensor_id: sensor for sensor in self.all_sensors}, self.decimals
        )

    def _sync_selection(self) -> None:
        by_id = {sensor.sensor_id: sensor for sensor in self.all_sensors}
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            sensor = by_id.get(item.data(Qt.ItemDataRole.UserRole))
            if sensor:
                sensor.selected_for_log = item.checkState() == Qt.CheckState.Checked
        self.selection_changed.emit()

    def _set_visible(self, selected: bool) -> None:
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self._sync_selection()

    def _reset_stats(self) -> None:
        for sensor in self.all_sensors:
            sensor.statistics.reset()
        self.refresh()

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hwlogger.models.sensor import Sensor
from hwlogger.utils.units import format_value_with_unit
from hwlogger.widgets.live_graph import LiveGraph


class GraphsTab(QWidget):
    def __init__(self, max_lines: int = 8, max_points: int = 36_000) -> None:
        super().__init__()
        self.max_lines = min(8, max(1, max_lines))
        self.sensors: dict[str, Sensor] = {}
        self.paused = False
        self.selector = QListWidget()
        self.selector.setMinimumWidth(240)
        self.graph = LiveGraph(max_points)
        self.history = QComboBox()
        for minutes in (1, 5, 10, 30, 60):
            self.history.addItem(f"{minutes} мин", minutes * 60)
        self.history.setCurrentIndex(1)
        self.pause = QPushButton("Пауза")
        self.pause.setCheckable(True)
        clear = QPushButton("Очистить историю")
        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d98c00")
        self.statistics = QTableWidget(0, 6)
        self.statistics.setHorizontalHeaderLabels(
            ["Датчик", "Сейчас", "Минимум", "Среднее", "Максимум", "Единица"]
        )
        controls = QHBoxLayout()
        controls.addWidget(QLabel("История:"))
        controls.addWidget(self.history)
        controls.addWidget(self.pause)
        controls.addWidget(clear)
        controls.addWidget(self.warning)
        controls.addStretch()
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addLayout(controls)
        right_layout.addWidget(self.graph, 1)
        right_layout.addWidget(self.statistics)
        splitter = QSplitter()
        splitter.addWidget(self.selector)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        self.selector.itemChanged.connect(self._selection_changed)
        self.history.currentIndexChanged.connect(
            lambda: self.graph.set_history_seconds(self.history.currentData())
        )
        self.pause.toggled.connect(self._pause_changed)
        clear.clicked.connect(self.graph.clear)

    def set_sensors(self, sensors: list[Sensor]) -> None:
        checked = {
            self.selector.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.selector.count())
            if self.selector.item(index).checkState() == Qt.CheckState.Checked
        }
        self.sensors = {sensor.sensor_id: sensor for sensor in sensors}
        self.selector.blockSignals(True)
        self.selector.clear()
        for sensor in sensors:
            item = QListWidgetItem(f"{sensor.name} [{sensor.unit}]")
            item.setData(Qt.ItemDataRole.UserRole, sensor.sensor_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if sensor.sensor_id in checked
                else Qt.CheckState.Unchecked
            )
            self.selector.addItem(item)
        self.selector.blockSignals(False)
        self._selection_changed()

    def _selected_ids(self) -> list[str]:
        return [
            self.selector.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.selector.count())
            if self.selector.item(index).checkState() == Qt.CheckState.Checked
        ]

    def _selection_changed(self, changed_item: QListWidgetItem | None = None) -> None:
        selected_ids = self._selected_ids()
        if len(selected_ids) > self.max_lines:
            sender = changed_item or self.selector.currentItem()
            if sender is not None:
                self.selector.blockSignals(True)
                sender.setCheckState(Qt.CheckState.Unchecked)
                self.selector.blockSignals(False)
            selected_ids = self._selected_ids()
            self.warning.setText(f"Можно выбрать не более {self.max_lines} датчиков")
        selected = [
            (sensor_id, self.sensors[sensor_id].name, self.sensors[sensor_id].unit)
            for sensor_id in selected_ids
            if sensor_id in self.sensors
        ]
        self.graph.set_selected(selected)
        units = {unit for _sensor_id, _name, unit in selected if unit}
        if len(units) > 1:
            self.warning.setText("Смешаны несовместимые единицы")
        elif len(selected_ids) <= self.max_lines:
            self.warning.setText("")
        self._update_statistics()

    def _pause_changed(self, paused: bool) -> None:
        self.paused = paused
        self.pause.setText("Продолжить" if paused else "Пауза")

    def update_values(self, values: dict[str, float | str | None]) -> None:
        if not self.paused:
            self.graph.append(values)
            self._update_statistics()

    def _update_statistics(self) -> None:
        selected_ids = self._selected_ids()
        self.statistics.setRowCount(len(selected_ids))
        for row, sensor_id in enumerate(selected_ids):
            sensor = self.sensors.get(sensor_id)
            if sensor is None:
                continue
            values = self.graph.visible_values(sensor_id)
            current = values[-1] if values else None
            minimum = min(values) if values else None
            maximum = max(values) if values else None
            average = sum(values) / len(values) if values else None
            row_values = [
                sensor.name,
                format_value_with_unit(current, sensor.unit),
                format_value_with_unit(minimum, sensor.unit),
                format_value_with_unit(average, sensor.unit),
                format_value_with_unit(maximum, sensor.unit),
                sensor.unit,
            ]
            for column, value in enumerate(row_values):
                self.statistics.setItem(row, column, QTableWidgetItem(value))

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
    selection_changed = Signal(list)

    def __init__(
        self,
        max_lines: int = 8,
        max_points: int = 36_000,
        selected_sensor_ids: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.max_lines = min(8, max(1, max_lines))
        self.sensors: dict[str, Sensor] = {}
        self._desired_sensor_ids = list(
            dict.fromkeys(selected_sensor_ids or [])
        )[: self.max_lines]
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
        self.sensors = {sensor.sensor_id: sensor for sensor in sensors}
        self.selector.blockSignals(True)
        self.selector.clear()
        for sensor in sensors:
            item = QListWidgetItem(f"{sensor.name} [{sensor.unit}]")
            item.setData(Qt.ItemDataRole.UserRole, sensor.sensor_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if sensor.sensor_id in self._desired_sensor_ids
                else Qt.CheckState.Unchecked
            )
            self.selector.addItem(item)
        self.selector.blockSignals(False)
        self._selection_changed(emit=False)

    def _selected_ids(self) -> list[str]:
        checked = set(self._checked_ids())
        return [
            sensor_id
            for sensor_id in self._desired_sensor_ids
            if sensor_id in checked
        ]

    def _selection_changed(
        self,
        changed_item: QListWidgetItem | None = None,
        emit: bool = True,
    ) -> None:
        checked_ids = self._checked_ids()
        known_ids = set(self.sensors)
        self._desired_sensor_ids = [
            sensor_id
            for sensor_id in self._desired_sensor_ids
            if sensor_id not in known_ids or sensor_id in checked_ids
        ]
        for sensor_id in checked_ids:
            if sensor_id not in self._desired_sensor_ids:
                self._desired_sensor_ids.append(sensor_id)
        if len(self._desired_sensor_ids) > self.max_lines:
            sender = changed_item or self.selector.currentItem()
            if sender is not None:
                sensor_id = sender.data(Qt.ItemDataRole.UserRole)
                self.selector.blockSignals(True)
                sender.setCheckState(Qt.CheckState.Unchecked)
                self.selector.blockSignals(False)
                if sensor_id in self._desired_sensor_ids:
                    self._desired_sensor_ids.remove(sensor_id)
            self.warning.setText(f"Можно выбрать не более {self.max_lines} датчиков")
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
            (
                sensor_id,
                self.sensors[sensor_id].name,
                self.sensors[sensor_id].unit,
                self.sensors[sensor_id].sensor_type,
            )
            for sensor_id in selected_ids
            if sensor_id in self.sensors and self.sensors[sensor_id].available
        ]
        self.graph.set_selected(selected)
        if len(selected_ids) <= self.max_lines:
            self.warning.setText("")
        self._update_statistics()
        if emit:
            self.selection_changed.emit(list(self._desired_sensor_ids))

    def _checked_ids(self) -> list[str]:
        return [
            self.selector.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.selector.count())
            if self.selector.item(index).checkState() == Qt.CheckState.Checked
        ]

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

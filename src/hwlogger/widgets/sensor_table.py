from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
)

from hwlogger.models.sensor import Sensor
from hwlogger.utils.units import format_value

HEADERS = [
    "Запись", "Имя", "Исходное имя", "Источник", "Тип", "Значение", "Единица",
    "Минимум", "Среднее", "Максимум", "Состояние", "ID / путь",
]


class SensorTable(QTableWidget):
    selection_changed = Signal()

    def __init__(self) -> None:
        super().__init__(0, len(HEADERS))
        self.setHorizontalHeaderLabels(HEADERS)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(False)
        for column, width in enumerate((65, 180, 130, 120, 105, 90, 70, 90, 90, 90, 180, 320)):
            self.setColumnWidth(column, width)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.itemChanged.connect(self._item_changed)

    def set_sensors(self, sensors: list[Sensor], decimals: int) -> None:
        sort_column = self.horizontalHeader().sortIndicatorSection()
        order = self.horizontalHeader().sortIndicatorOrder()
        self.setSortingEnabled(False)
        self.blockSignals(True)
        self.setRowCount(len(sensors))
        for row, sensor in enumerate(sensors):
            checkbox = QTableWidgetItem()
            checkbox.setFlags(checkbox.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            checkbox.setCheckState(
                Qt.CheckState.Checked if sensor.selected_for_log else Qt.CheckState.Unchecked
            )
            checkbox.setData(Qt.ItemDataRole.UserRole, sensor.sensor_id)
            stats = sensor.statistics
            values = [
                checkbox,
                QTableWidgetItem(sensor.name),
                QTableWidgetItem(sensor.original_name),
                QTableWidgetItem(sensor.source),
                QTableWidgetItem(sensor.sensor_type.value),
                QTableWidgetItem(format_value(sensor.value, decimals)),
                QTableWidgetItem(sensor.unit),
                QTableWidgetItem(format_value(stats.minimum, decimals)),
                QTableWidgetItem(format_value(stats.average, decimals)),
                QTableWidgetItem(format_value(stats.maximum, decimals)),
                QTableWidgetItem(
                    "Доступен" if sensor.available else f"Недоступен: {sensor.last_error}"
                ),
                QTableWidgetItem(sensor.backend_id),
            ]
            for column, item in enumerate(values):
                item.setData(Qt.ItemDataRole.UserRole + 1, sensor.sensor_id)
                self.setItem(row, column, item)
        self.blockSignals(False)
        self.setSortingEnabled(True)
        self.sortItems(sort_column, order)

    def update_sensor_values(self, sensors: dict[str, Sensor], decimals: int) -> int:
        """Apply value/statistics changes on the GUI thread and emit model dataChanged."""
        if QThread.currentThread() != self.thread():
            raise RuntimeError("Sensor table update attempted outside the GUI thread")
        changed_rows = 0
        self.setSortingEnabled(False)
        for row in range(self.rowCount()):
            sensor_id = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
            sensor = sensors.get(sensor_id)
            if sensor is None:
                continue
            stats = sensor.statistics
            texts = {
                5: format_value(sensor.value, decimals),
                7: format_value(stats.minimum, decimals),
                8: format_value(stats.average, decimals),
                9: format_value(stats.maximum, decimals),
                10: (
                    "Доступен"
                    if sensor.available
                    else f"Недоступен: {sensor.last_error}"
                ),
            }
            row_changed = False
            for column, text in texts.items():
                item = self.item(row, column)
                if item.text() != text:
                    item.setText(text)
                    row_changed = True
            changed_rows += int(row_changed)
        self.setSortingEnabled(True)
        return changed_rows

    def _item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            self.selection_changed.emit()

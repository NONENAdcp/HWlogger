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
from hwlogger.utils.units import format_value_with_unit

HEADERS = [
    "Запись", "Имя", "Исходное имя", "Источник", "Тип", "Сейчас",
    "Минимум", "Среднее", "Максимум", "Состояние", "Путь",
]
TECHNICAL_COLUMNS = (2, 3, 4, 10)
WIDTH_KEYS = {
    0: "record", 1: "name", 2: "original_name", 3: "source", 4: "type",
    5: "current", 6: "minimum", 7: "average", 8: "maximum",
    9: "status", 10: "path",
}


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
        for column, width in enumerate(
            (54, 230, 130, 120, 105, 100, 100, 100, 100, 105, 320)
        ):
            self.setColumnWidth(column, width)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.itemChanged.connect(self._item_changed)

    def set_sensors(self, sensors: list[Sensor], decimals: int = 0) -> None:
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
                QTableWidgetItem(
                    format_value_with_unit(sensor.value, sensor.unit, decimals)
                ),
                QTableWidgetItem(
                    format_value_with_unit(stats.minimum, sensor.unit, decimals)
                ),
                QTableWidgetItem(
                    format_value_with_unit(stats.average, sensor.unit, decimals)
                ),
                QTableWidgetItem(
                    format_value_with_unit(stats.maximum, sensor.unit, decimals)
                ),
                QTableWidgetItem("Доступен" if sensor.available else "Недоступен"),
                QTableWidgetItem(sensor.backend_id),
            ]
            for column, item in enumerate(values):
                item.setData(Qt.ItemDataRole.UserRole + 1, sensor.sensor_id)
                if column == 9 and sensor.last_error:
                    item.setToolTip(sensor.last_error)
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
                5: format_value_with_unit(sensor.value, sensor.unit, decimals),
                6: format_value_with_unit(stats.minimum, sensor.unit, decimals),
                7: format_value_with_unit(stats.average, sensor.unit, decimals),
                8: format_value_with_unit(stats.maximum, sensor.unit, decimals),
                9: "Доступен" if sensor.available else "Недоступен",
            }
            row_changed = False
            for column, text in texts.items():
                item = self.item(row, column)
                if item.text() != text:
                    item.setText(text)
                    row_changed = True
                if column == 9:
                    item.setToolTip(sensor.last_error)
            changed_rows += int(row_changed)
        self.setSortingEnabled(True)
        return changed_rows

    def set_technical_columns_visible(self, visible: bool) -> None:
        for column in TECHNICAL_COLUMNS:
            self.setColumnHidden(column, not visible)

    def column_widths(self) -> dict[str, int]:
        return {
            WIDTH_KEYS[column]: self.columnWidth(column)
            for column in range(self.columnCount())
        }

    def restore_column_widths(self, widths: dict[str, int]) -> None:
        for column, key in WIDTH_KEYS.items():
            width = widths.get(key)
            if isinstance(width, int) and 30 <= width <= 2000:
                self.setColumnWidth(column, width)

    def _item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            self.selection_changed.emit()

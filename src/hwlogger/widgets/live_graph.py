from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


@dataclass(slots=True)
class GraphSeries:
    timestamps: deque[float]
    values: deque[float]
    curve: pg.PlotDataItem
    unit: str
    current: float | None = None


class LiveGraph(QWidget):
    def __init__(self, max_points: int = 36_000) -> None:
        super().__init__()
        self.max_points = max_points
        self.history_seconds = 300
        self.series: dict[str, GraphSeries] = {}
        axis = pg.DateAxisItem(orientation="bottom")
        self.plot = pg.PlotWidget(axisItems={"bottom": axis})
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.addLegend()
        self.plot.setLabel("bottom", "Время")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)

    def set_history_seconds(self, seconds: int) -> None:
        self.history_seconds = seconds
        self.refresh()

    def set_selected(self, selected: list[tuple[str, str, str]]) -> None:
        selected_ids = {sensor_id for sensor_id, _name, _unit in selected}
        for sensor_id in list(self.series):
            if sensor_id not in selected_ids:
                self.plot.removeItem(self.series.pop(sensor_id).curve)
        colors = [
            "#4FC3F7", "#FFB74D", "#81C784", "#E57373",
            "#BA68C8", "#FFF176", "#4DB6AC", "#F06292",
        ]
        for index, (sensor_id, name, unit) in enumerate(selected):
            if sensor_id in self.series:
                continue
            curve = self.plot.plot(
                [], [], name=name, pen=pg.mkPen(colors[index % len(colors)], width=2)
            )
            self.series[sensor_id] = GraphSeries(
                deque(maxlen=self.max_points),
                deque(maxlen=self.max_points),
                curve,
                unit,
            )
        self.refresh()

    def append(self, values: dict[str, float | str | None]) -> None:
        timestamp = time.time()
        for sensor_id, series in self.series.items():
            value = values.get(sensor_id)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                series.timestamps.append(timestamp)
                series.values.append(float(value))
                series.current = float(value)
        self.refresh()

    def refresh(self) -> None:
        cutoff = time.time() - self.history_seconds
        for series in self.series.values():
            start = 0
            for index, timestamp in enumerate(series.timestamps):
                if timestamp >= cutoff:
                    start = index
                    break
            series.curve.setData(
                list(series.timestamps)[start:], list(series.values)[start:]
            )

    def clear(self) -> None:
        for series in self.series.values():
            series.timestamps.clear()
            series.values.clear()
            series.current = None
            series.curve.setData([], [])

    def visible_values(self, sensor_id: str) -> list[float]:
        series = self.series.get(sensor_id)
        if series is None:
            return []
        cutoff = time.time() - self.history_seconds
        return [
            value
            for timestamp, value in zip(series.timestamps, series.values, strict=True)
            if timestamp >= cutoff
        ]

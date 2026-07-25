from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from hwlogger.models.sensor import SensorType

LINE_COLORS = (
    "#4FC3F7",
    "#FFB74D",
    "#81C784",
    "#E57373",
    "#BA68C8",
    "#FFF176",
    "#4DB6AC",
    "#F06292",
)


@dataclass(frozen=True, slots=True)
class GraphGroupKey:
    family: str
    unit: str


@dataclass(slots=True)
class GraphSeries:
    timestamps: deque[float]
    values: deque[float]
    curve: pg.PlotDataItem
    group: GraphGroupKey
    name: str
    current: float | None = None


@dataclass(slots=True)
class GraphGroup:
    plot: pg.PlotWidget
    sensor_ids: set[str] = field(default_factory=set)


def graph_group_key(sensor_type: SensorType, unit: str) -> GraphGroupKey:
    """Return a semantic and unit-safe scaling group."""
    families = {
        SensorType.TEMPERATURE: "temperature",
        SensorType.FREQUENCY: "frequency",
        SensorType.UTILIZATION: "percentage",
        SensorType.LOAD: "percentage",
        SensorType.POWER: "power",
        SensorType.VOLTAGE: "voltage",
        SensorType.CURRENT: "current",
        SensorType.ENERGY: "energy",
        SensorType.FAN: "fan",
        SensorType.MEMORY: "memory",
    }
    return GraphGroupKey(families.get(sensor_type, sensor_type.value), unit)


def sensor_color(sensor_id: str) -> str:
    digest = hashlib.sha256(sensor_id.encode("utf-8")).digest()
    return LINE_COLORS[int.from_bytes(digest[:2], "big") % len(LINE_COLORS)]


class LiveGraph(QWidget):
    def __init__(self, max_points: int = 36_000) -> None:
        super().__init__()
        self.max_points = max_points
        self.history_seconds = 300
        self.series: dict[str, GraphSeries] = {}
        self.groups: dict[GraphGroupKey, GraphGroup] = {}
        self._colors: dict[str, str] = {}
        self._first_timestamp: float | None = None
        self._latest_timestamp: float | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.placeholder = QLabel("Выберите датчики для графика")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.placeholder)

    def set_history_seconds(self, seconds: int) -> None:
        self.history_seconds = seconds
        self.refresh()

    def set_selected(
        self,
        selected: list[tuple[str, str, str, SensorType]],
    ) -> None:
        desired = {
            sensor_id: (name, graph_group_key(sensor_type, unit))
            for sensor_id, name, unit, sensor_type in selected
        }
        for sensor_id in list(self.series):
            series = self.series[sensor_id]
            metadata = desired.get(sensor_id)
            if metadata is None or metadata != (series.name, series.group):
                self._remove_series(sensor_id)

        for sensor_id, name, unit, sensor_type in selected:
            if sensor_id in self.series:
                continue
            key = graph_group_key(sensor_type, unit)
            group = self._ensure_group(key)
            color = self._color_for(sensor_id)
            legend_name = f"{name} [{unit}]" if unit else name
            curve = group.plot.plot(
                [],
                [],
                name=legend_name,
                pen=pg.mkPen(color, width=2),
                connect="finite",
            )
            group.sensor_ids.add(sensor_id)
            self.series[sensor_id] = GraphSeries(
                deque(maxlen=self.max_points),
                deque(maxlen=self.max_points),
                curve,
                key,
                name,
            )
        self._recalculate_timeline()
        self._sync_x_axes()
        self.placeholder.setVisible(not self.groups)
        self.refresh()

    def append(self, values: dict[str, float | str | None]) -> None:
        timestamp = time.time()
        appended = False
        for sensor_id, series in self.series.items():
            value = values.get(sensor_id)
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
            ):
                number = float(value)
                series.timestamps.append(timestamp)
                series.values.append(number)
                series.current = number
                appended = True
        if appended:
            if self._first_timestamp is None:
                self._first_timestamp = timestamp
            self._latest_timestamp = timestamp
        self.refresh()

    def refresh(self) -> None:
        time_range = self._time_range()
        cutoff = time_range[0] if time_range is not None else float("-inf")
        visible_by_group: dict[GraphGroupKey, list[float]] = {
            key: [] for key in self.groups
        }
        for series in self.series.values():
            timestamps = list(series.timestamps)
            values = list(series.values)
            start = next(
                (
                    index
                    for index, timestamp in enumerate(timestamps)
                    if timestamp >= cutoff
                ),
                len(timestamps),
            )
            visible_timestamps = timestamps[start:]
            visible_values = values[start:]
            series.curve.setData(visible_timestamps, visible_values)
            visible_by_group[series.group].extend(visible_values)

        for key, group in self.groups.items():
            group.plot.getViewBox().invertX(False)
            if key.family == "percentage":
                values = visible_by_group[key]
                lower = min([0.0, *values])
                upper = max([100.0, *values])
                if lower == upper:
                    upper = lower + 1.0
                group.plot.setYRange(lower, upper, padding=0.02)
            else:
                group.plot.enableAutoRange(axis="y", enable=True)

        if self.groups and time_range is not None:
            first_group = next(iter(self.groups.values()))
            first_group.plot.setXRange(*time_range, padding=0)

    def clear(self) -> None:
        for series in self.series.values():
            series.timestamps.clear()
            series.values.clear()
            series.current = None
            series.curve.setData([], [])
        self._first_timestamp = None
        self._latest_timestamp = None

    def visible_values(self, sensor_id: str) -> list[float]:
        series = self.series.get(sensor_id)
        if series is None:
            return []
        time_range = self._time_range()
        cutoff = time_range[0] if time_range is not None else float("-inf")
        return [
            value
            for timestamp, value in zip(series.timestamps, series.values, strict=True)
            if timestamp >= cutoff
        ]

    def _ensure_group(self, key: GraphGroupKey) -> GraphGroup:
        existing = self.groups.get(key)
        if existing is not None:
            return existing
        axis = pg.DateAxisItem(orientation="bottom")
        plot = pg.PlotWidget(axisItems={"bottom": axis})
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.addLegend()
        plot.setLabel("left", key.unit or key.family)
        plot.getAxis("left").setWidth(60)
        plot.setLabel("bottom", "Время")
        plot.enableAutoRange(axis="y", enable=True)
        group = GraphGroup(plot)
        self.groups[key] = group
        self._layout.addWidget(plot, 1)
        return group

    def _color_for(self, sensor_id: str) -> str:
        existing = self._colors.get(sensor_id)
        if existing is not None:
            return existing
        preferred = sensor_color(sensor_id)
        used = set(self._colors.values())
        start = LINE_COLORS.index(preferred)
        color = next(
            (
                LINE_COLORS[(start + offset) % len(LINE_COLORS)]
                for offset in range(len(LINE_COLORS))
                if LINE_COLORS[(start + offset) % len(LINE_COLORS)] not in used
            ),
            preferred,
        )
        self._colors[sensor_id] = color
        return color

    def _remove_series(self, sensor_id: str) -> None:
        series = self.series.pop(sensor_id)
        group = self.groups[series.group]
        group.plot.removeItem(series.curve)
        group.sensor_ids.discard(sensor_id)
        if not group.sensor_ids:
            self.groups.pop(series.group)
            self._layout.removeWidget(group.plot)
            group.plot.setParent(None)
            group.plot.deleteLater()

    def _sync_x_axes(self) -> None:
        if not self.groups:
            return
        plots = [group.plot for group in self.groups.values()]
        primary = plots[0].getPlotItem()
        primary.setXLink(None)
        for plot in plots[1:]:
            plot.getPlotItem().setXLink(primary)
        for plot in plots:
            plot.getViewBox().invertX(False)
        for index, plot in enumerate(plots):
            bottom = plot.getAxis("bottom")
            bottom.setStyle(showValues=index == len(plots) - 1)
            plot.setLabel("bottom", "Время" if index == len(plots) - 1 else "")

    def _time_range(self) -> tuple[float, float] | None:
        if self._first_timestamp is None or self._latest_timestamp is None:
            return None
        if self._latest_timestamp - self._first_timestamp < self.history_seconds:
            return (
                self._first_timestamp,
                self._first_timestamp + self.history_seconds,
            )
        return (
            self._latest_timestamp - self.history_seconds,
            self._latest_timestamp,
        )

    def _recalculate_timeline(self) -> None:
        first = [
            series.timestamps[0]
            for series in self.series.values()
            if series.timestamps
        ]
        latest = [
            series.timestamps[-1]
            for series in self.series.values()
            if series.timestamps
        ]
        self._first_timestamp = min(first) if first else None
        self._latest_timestamp = max(latest) if latest else None

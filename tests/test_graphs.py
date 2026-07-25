from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt

from hwlogger.backends.fake import FakeSensorBackend
from hwlogger.models.sensor import Sensor, SensorCategory, SensorType
from hwlogger.ui.graphs_tab import GraphsTab
from hwlogger.widgets.live_graph import (
    LiveGraph,
    graph_group_key,
    sensor_color,
)


def _sensor(
    sensor_id: str,
    sensor_type: SensorType,
    unit: str,
    name: str | None = None,
) -> Sensor:
    return Sensor(
        sensor_id=sensor_id,
        name=name or sensor_id,
        original_name=sensor_id,
        source="test",
        category=SensorCategory.OTHER,
        sensor_type=sensor_type,
        unit=unit,
        backend_id=sensor_id,
        reader=lambda: None,
    )


def _selection(sensor: Sensor) -> tuple[str, str, str, SensorType]:
    return sensor.sensor_id, sensor.name, sensor.unit, sensor.sensor_type


def test_incompatible_sensor_types_have_independent_groups(qtbot):
    temperature = _sensor("temp", SensorType.TEMPERATURE, "°C")
    frequency = _sensor("freq", SensorType.FREQUENCY, "MHz")
    power = _sensor("power", SensorType.POWER, "W")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_selected(
        [_selection(temperature), _selection(frequency), _selection(power)]
    )

    assert graph.series["temp"].group != graph.series["freq"].group
    assert graph.series["temp"].group != graph.series["power"].group
    assert len(graph.groups) == 3
    assert len({id(group.plot) for group in graph.groups.values()}) == 3


def test_compatible_temperatures_and_frequencies_share_their_groups(qtbot):
    sensors = [
        _sensor("temp-1", SensorType.TEMPERATURE, "°C"),
        _sensor("temp-2", SensorType.TEMPERATURE, "°C"),
        _sensor("freq-1", SensorType.FREQUENCY, "MHz"),
        _sensor("freq-2", SensorType.FREQUENCY, "MHz"),
    ]
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor) for sensor in sensors])

    assert graph.series["temp-1"].group == graph.series["temp-2"].group
    assert graph.series["freq-1"].group == graph.series["freq-2"].group
    assert graph.series["temp-1"].group != graph.series["freq-1"].group
    assert len(graph.groups) == 2


def test_grouping_uses_semantic_type_and_unit():
    assert graph_group_key(
        SensorType.UTILIZATION, "%"
    ) == graph_group_key(SensorType.LOAD, "%")
    assert graph_group_key(
        SensorType.TEMPERATURE, "°C"
    ) != graph_group_key(SensorType.POWER, "°C")
    assert graph_group_key(
        SensorType.MEMORY, "MiB"
    ) != graph_group_key(SensorType.MEMORY, "GiB")


def test_groups_exist_only_for_selected_sensors_and_are_removed(qtbot):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    assert not graph.groups

    graph.set_selected([_selection(sensor)])
    assert len(graph.groups) == 1
    graph.set_selected([])
    assert not graph.groups
    assert not graph.series
    assert graph.placeholder.isVisible() or graph.isHidden()


def test_color_is_stable_across_updates_and_recreation(qtbot):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor)])
    first = graph.series["temp"].curve.opts["pen"].color().name()
    graph.append({"temp": 50.0})
    assert graph.series["temp"].curve.opts["pen"].color().name() == first

    graph.set_selected([])
    graph.set_selected([_selection(sensor)])
    assert graph.series["temp"].curve.opts["pen"].color().name() == first
    assert first == sensor_color("temp").lower()


def test_invalid_values_are_ignored_but_zero_is_recorded(qtbot):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor)])
    for value in (None, "bad", math.nan, math.inf, -math.inf, 0):
        graph.append({"temp": value})
    assert list(graph.series["temp"].values) == [0.0]


def test_live_graph_buffer_is_bounded_for_every_series(qtbot):
    sensors = [
        _sensor("temp", SensorType.TEMPERATURE, "°C"),
        _sensor("freq", SensorType.FREQUENCY, "MHz"),
    ]
    graph = LiveGraph(max_points=5)
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor) for sensor in sensors])
    for value in range(12):
        graph.append({"temp": value, "freq": value * 100})
    assert list(graph.series["temp"].values) == [7, 8, 9, 10, 11]
    assert list(graph.series["freq"].values) == [700, 800, 900, 1000, 1100]


def test_rescan_does_not_duplicate_curves_or_legend_entries(qtbot):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    selected = [_selection(sensor)]
    graph.set_selected(selected)
    curve = graph.series["temp"].curve
    graph.set_selected(selected)
    group = next(iter(graph.groups.values()))

    assert graph.series["temp"].curve is curve
    assert len(group.sensor_ids) == 1
    assert len(group.plot.getPlotItem().legend.items) == 1

    graph.set_selected([])
    assert not graph.series
    assert not graph.groups


def test_disappeared_sensor_is_removed_from_graph_and_legend(qtbot):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    tab = GraphsTab()
    qtbot.addWidget(tab)
    tab.set_sensors([sensor])
    tab.selector.item(0).setCheckState(Qt.CheckState.Checked)
    assert "temp" in tab.graph.series

    sensor.available = False
    tab.set_sensors([sensor])
    assert "temp" not in tab.graph.series
    assert not tab.graph.groups


def test_fake_sensors_create_expected_independent_active_groups(qtbot):
    sensors = FakeSensorBackend().scan()
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor) for sensor in sensors])
    families = {key.family for key in graph.groups}
    assert {"temperature", "frequency", "percentage", "power"} <= families


def test_group_ranges_are_independent(qtbot):
    temperature = _sensor("temp", SensorType.TEMPERATURE, "°C")
    frequency = _sensor("freq", SensorType.FREQUENCY, "MHz")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.resize(900, 600)
    graph.show()
    graph.set_selected([_selection(temperature), _selection(frequency)])
    graph.append({"temp": 40.0, "freq": 1000.0})
    graph.append({"temp": 90.0, "freq": 5000.0})
    qtbot.wait(50)

    temp_plot = graph.groups[graph.series["temp"].group].plot
    freq_plot = graph.groups[graph.series["freq"].group].plot
    temp_range = temp_plot.viewRange()[1]
    freq_range = freq_plot.viewRange()[1]
    assert temp_range[1] < 200
    assert freq_range[1] > 1000

    graph.append({"temp": None, "freq": 4000.0})
    qtbot.wait(20)
    assert temp_plot.viewRange()[1] == temp_range
    graph.append({"temp": 60.0, "freq": None})
    qtbot.wait(20)
    assert freq_plot.viewRange()[1] == freq_range


def test_percentage_group_uses_logical_range_and_accepts_above_100(qtbot):
    sensor = _sensor("load", SensorType.UTILIZATION, "%")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor)])
    graph.append({"load": 120.0})
    plot = graph.groups[graph.series["load"].group].plot
    lower, upper = plot.viewRange()[1]
    assert lower <= 0
    assert upper >= 120


def test_graphs_tab_limits_selection_to_eight_and_pause_freezes(qtbot):
    sensors = [FakeSensorBackend().scan()[0] for _index in range(9)]
    for index, sensor in enumerate(sensors):
        sensor.sensor_id = f"fake:{index}"
    tab = GraphsTab(max_lines=8)
    qtbot.addWidget(tab)
    tab.set_sensors(sensors)
    for index in range(9):
        tab.selector.setCurrentRow(index)
        tab.selector.item(index).setCheckState(Qt.CheckState.Checked)
    assert len(tab._selected_ids()) == 8
    selected = tab._selected_ids()[0]
    tab.update_values({selected: 10.0})
    before = len(tab.graph.series[selected].values)
    tab.pause.setChecked(True)
    tab.update_values({selected: 20.0})
    assert len(tab.graph.series[selected].values) == before


def test_graph_widget_closes_and_repeated_selection_does_not_grow(qtbot):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    selected = [_selection(sensor)]
    for _index in range(20):
        graph.set_selected(selected)
    assert len(graph.groups) == 1
    assert len(graph.series) == 1
    graph.close()


def test_time_coordinates_grow_and_new_points_are_on_the_right(qtbot, monkeypatch):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.resize(800, 400)
    graph.show()
    graph.set_selected([_selection(sensor)])
    clock = [1000.0]
    monkeypatch.setattr("hwlogger.widgets.live_graph.time.time", lambda: clock[0])
    graph.append({"temp": 40.0})
    clock[0] = 1001.0
    graph.append({"temp": 41.0})
    qtbot.wait(20)

    timestamps = list(graph.series["temp"].timestamps)
    curve_x, _curve_y = graph.series["temp"].curve.getData()
    view_box = next(iter(graph.groups.values())).plot.getViewBox()
    old_position = view_box.mapViewToScene(QPointF(timestamps[0], 40.0)).x()
    new_position = view_box.mapViewToScene(QPointF(timestamps[1], 41.0)).x()
    x_range = view_box.viewRange()[0]

    assert timestamps == sorted(timestamps)
    assert list(curve_x) == timestamps
    assert old_position < new_position
    assert x_range[0] == timestamps[0]
    assert timestamps[0] < timestamps[-1] < x_range[1]
    assert not view_box.state["xInverted"]


def test_linked_groups_share_forward_time_range(qtbot, monkeypatch):
    sensors = [
        _sensor("temp", SensorType.TEMPERATURE, "°C"),
        _sensor("freq", SensorType.FREQUENCY, "MHz"),
    ]
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.show()
    graph.set_selected([_selection(sensor) for sensor in sensors])
    monkeypatch.setattr("hwlogger.widgets.live_graph.time.time", lambda: 2000.0)
    graph.append({"temp": 50.0, "freq": 2000.0})
    qtbot.wait(20)

    view_boxes = [group.plot.getViewBox() for group in graph.groups.values()]
    ranges = [view_box.viewRange()[0] for view_box in view_boxes]
    assert ranges[0] == ranges[1]
    assert ranges[0][0] < ranges[0][1]
    assert all(not view_box.state["xInverted"] for view_box in view_boxes)


def test_refresh_restores_forward_direction_for_every_group(qtbot):
    sensors = [
        _sensor("temp", SensorType.TEMPERATURE, "°C"),
        _sensor("freq", SensorType.FREQUENCY, "MHz"),
    ]
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor) for sensor in sensors])
    for group in graph.groups.values():
        group.plot.getViewBox().invertX(True)
    graph.refresh()
    assert all(
        not group.plot.getViewBox().state["xInverted"]
        for group in graph.groups.values()
    )


def test_bounded_history_keeps_time_order(qtbot, monkeypatch):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph(max_points=3)
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor)])
    clock = [0.0]
    monkeypatch.setattr("hwlogger.widgets.live_graph.time.time", lambda: clock[0])
    for index in range(6):
        clock[0] = float(index)
        graph.append({"temp": float(index)})
    assert list(graph.series["temp"].timestamps) == [3.0, 4.0, 5.0]
    assert list(graph.series["temp"].values) == [3.0, 4.0, 5.0]


def test_missing_and_non_finite_values_do_not_break_time_order(qtbot, monkeypatch):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_selected([_selection(sensor)])
    clock = [10.0]
    monkeypatch.setattr("hwlogger.widgets.live_graph.time.time", lambda: clock[0])
    for timestamp, value in (
        (10.0, 1.0),
        (11.0, None),
        (12.0, math.nan),
        (13.0, math.inf),
        (14.0, 2.0),
    ):
        clock[0] = timestamp
        graph.append({"temp": value})
    assert list(graph.series["temp"].timestamps) == [10.0, 14.0]
    assert list(graph.series["temp"].values) == [1.0, 2.0]


def test_first_point_starts_left_with_future_space(qtbot, monkeypatch):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_history_seconds(60)
    graph.set_selected([_selection(sensor)])
    monkeypatch.setattr("hwlogger.widgets.live_graph.time.time", lambda: 100.0)
    graph.append({"temp": 40.0})
    x_range = next(iter(graph.groups.values())).plot.viewRange()[0]
    assert x_range == [100.0, 160.0]
    assert graph.series["temp"].timestamps[0] == x_range[0]


def test_time_window_stays_fixed_then_scrolls(qtbot, monkeypatch):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_history_seconds(10)
    graph.set_selected([_selection(sensor)])
    clock = [100.0]
    monkeypatch.setattr("hwlogger.widgets.live_graph.time.time", lambda: clock[0])

    graph.append({"temp": 40.0})
    clock[0] = 105.0
    graph.append({"temp": 45.0})
    assert next(iter(graph.groups.values())).plot.viewRange()[0] == [100.0, 110.0]

    clock[0] = 110.0
    graph.append({"temp": 50.0})
    assert next(iter(graph.groups.values())).plot.viewRange()[0] == [100.0, 110.0]

    clock[0] = 115.0
    graph.append({"temp": 55.0})
    x_range = next(iter(graph.groups.values())).plot.viewRange()[0]
    curve_x, _curve_y = graph.series["temp"].curve.getData()
    assert x_range == [105.0, 115.0]
    assert curve_x[0] == 105.0
    assert 100.0 not in curve_x


def test_remove_and_readd_starts_new_forward_window(qtbot, monkeypatch):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_history_seconds(30)
    selected = [_selection(sensor)]
    clock = [100.0]
    monkeypatch.setattr("hwlogger.widgets.live_graph.time.time", lambda: clock[0])
    graph.set_selected(selected)
    graph.append({"temp": 40.0})
    graph.set_selected([])

    clock[0] = 200.0
    graph.set_selected(selected)
    graph.append({"temp": 50.0})
    assert next(iter(graph.groups.values())).plot.viewRange()[0] == [200.0, 230.0]


def test_rescan_preserves_initial_forward_window(qtbot, monkeypatch):
    sensor = _sensor("temp", SensorType.TEMPERATURE, "°C")
    graph = LiveGraph()
    qtbot.addWidget(graph)
    graph.set_history_seconds(30)
    selected = [_selection(sensor)]
    clock = [100.0]
    monkeypatch.setattr("hwlogger.widgets.live_graph.time.time", lambda: clock[0])
    graph.set_selected(selected)
    graph.append({"temp": 40.0})
    graph.set_selected(selected)
    clock[0] = 105.0
    graph.append({"temp": 45.0})
    assert next(iter(graph.groups.values())).plot.viewRange()[0] == [100.0, 130.0]

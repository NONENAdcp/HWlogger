from PySide6.QtCore import Qt

from hwlogger.backends.fake import FakeSensorBackend
from hwlogger.ui.graphs_tab import GraphsTab
from hwlogger.widgets.live_graph import LiveGraph


def test_live_graph_buffer_is_bounded(qtbot):
    graph = LiveGraph(max_points=5)
    qtbot.addWidget(graph)
    graph.set_selected([("sensor", "Датчик", "°C")])
    for value in range(12):
        graph.append({"sensor": value})
    assert list(graph.series["sensor"].values) == [7, 8, 9, 10, 11]


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

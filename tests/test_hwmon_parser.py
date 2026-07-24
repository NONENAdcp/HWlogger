from pathlib import Path

from hwlogger.backends.hwmon import HwmonBackend, stable_sensor_id


def test_stable_sensor_id():
    path = Path("/devices/platform/coretemp")
    assert stable_sensor_id(path, "temp1_input") == stable_sensor_id(path, "temp1_input")
    assert stable_sensor_id(path, "temp1_input") != stable_sensor_id(path, "temp2_input")


def test_hwmon_scan_and_disappearance(tmp_path):
    root = tmp_path / "hwmon"
    device = root / "hwmon0"
    device.mkdir(parents=True)
    (device / "name").write_text("coretemp\n")
    (device / "temp1_input").write_text("42000\n")
    (device / "temp1_label").write_text("Package id 0\n")
    sensors = HwmonBackend(root).scan()
    assert len(sensors) == 1
    assert sensors[0].read() == 42.0
    (device / "temp1_input").unlink()
    assert sensors[0].read() is None
    assert not sensors[0].available


def test_known_hwmon_names_are_russian_and_raw_name_is_preserved(tmp_path):
    root = tmp_path / "hwmon"
    device = root / "hwmon0"
    device.mkdir(parents=True)
    (device / "name").write_text("coretemp\n")
    (device / "temp1_input").write_text("63000\n")
    (device / "temp1_label").write_text("Package id 0\n")
    sensor = HwmonBackend(root).scan()[0]
    assert sensor.name == "Температура CPU"
    assert sensor.original_name == "temp1_input"
    assert sensor.backend_id.endswith("/temp1_input")


def test_unknown_thinkpad_ec_name_is_neutral(tmp_path):
    root = tmp_path / "hwmon"
    device = root / "hwmon0"
    device.mkdir(parents=True)
    (device / "name").write_text("thinkpad\n")
    (device / "temp3_input").write_text("41000\n")
    sensor = HwmonBackend(root).scan()[0]
    assert sensor.name == "Датчик EC temp3"

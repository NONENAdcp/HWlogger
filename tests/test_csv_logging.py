import csv

from hwlogger.models.sensor import Sensor, SensorCategory, SensorType
from hwlogger.services.logging_service import LoggingService


def make_sensor(sensor_id="test:temperature"):
    return Sensor(
        sensor_id=sensor_id,
        name="Temperature",
        original_name="temp1_input",
        source="test",
        category=SensorCategory.CPU,
        sensor_type=SensorType.TEMPERATURE,
        unit="°C",
        backend_id="/test/temp1_input",
        reader=lambda: 0.0,
    )


def test_csv_and_summary_preserve_zero(tmp_path):
    service = LoggingService()
    session = service.start(tmp_path, [make_sensor()], flush_rows=1)
    service.write_row({"test:temperature": 0.0})
    service.write_row({"test:temperature": None})
    completed = service.stop()
    assert completed == session
    with session.csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows[1][-1] == "0.0"
    assert rows[2][-1] == ""
    with session.summary_path.open(newline="", encoding="utf-8") as stream:
        summary = list(csv.DictReader(stream))
    assert summary[0]["valid_count"] == "1"
    assert summary[0]["minimum"] == "0.0"


def test_unique_names_and_restart(tmp_path):
    service = LoggingService()
    first = service.start(tmp_path, [make_sensor()])
    service.stop()
    second = service.start(tmp_path, [make_sensor()])
    service.stop()
    assert first.csv_path != second.csv_path

import csv
import json

import pytest

from hwlogger.services.log_reader import (
    analyze_interval,
    discover_sessions,
    preview_csv,
)


def _write_session(tmp_path, row_count=1000):
    csv_path = tmp_path / "hwlog_2026-01-01_12-00-00.csv"
    metadata_path = tmp_path / "hwlog_2026-01-01_12-00-00.json"
    summary_path = tmp_path / "hwlog_2026-01-01_12-00-00_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["timestamp_local", "timestamp_utc", "elapsed_seconds", "CPU [°C]", "Fan [RPM]"]
        )
        for index in range(row_count):
            writer.writerow(["local", "utc", index, index % 100, 0 if index % 2 else 1000])
    metadata_path.write_text(
        json.dumps(
            {
                "started_at": "2026-01-01T12:00:00+00:00",
                "ended_at": f"2026-01-01T12:{row_count // 60:02}:00+00:00",
                "duration_seconds": row_count,
                "rows": row_count,
                "sensors": [
                    {
                        "column": "CPU [°C]",
                        "sensor_id": "cpu-temp",
                        "name": "Температура CPU",
                        "type": "temperature",
                        "unit": "°C",
                    },
                    {
                        "column": "Fan [RPM]",
                        "sensor_id": "fan",
                        "name": "Вентилятор",
                        "type": "fan",
                        "unit": "RPM",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    summary_path.write_text("name,minimum,average,maximum,unit,valid_count\n", encoding="utf-8")
    return csv_path, metadata_path


def test_discovery_links_csv_metadata_and_summary(tmp_path):
    _write_session(tmp_path, 60)
    sessions = discover_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].rows == 60
    assert sessions[0].sensor_count == 2
    assert sessions[0].summary_path is not None


def test_preview_reads_only_requested_edges(tmp_path):
    csv_path, _ = _write_session(tmp_path, 100)
    header, first, last = preview_csv(csv_path, 3, 4)
    assert header[2] == "elapsed_seconds"
    assert [row[2] for row in first] == ["0", "1", "2"]
    assert [row[2] for row in last] == ["96", "97", "98", "99"]


def test_streaming_interval_analysis_counts_zero(tmp_path):
    csv_path, metadata_path = _write_session(tmp_path, 10_000)
    result = analyze_interval(csv_path, metadata_path, 100, 199)
    temperature = next(row for row in result if row.sensor_id == "cpu-temp")
    fan = next(row for row in result if row.sensor_id == "fan")
    assert temperature.count == 100
    assert temperature.minimum == 0
    assert temperature.maximum == 99
    assert fan.count == 100
    assert fan.minimum == 0
    assert fan.maximum == 1000
    assert temperature.duration_seconds == 99


def test_streaming_analysis_can_be_cancelled(tmp_path):
    csv_path, metadata_path = _write_session(tmp_path, 100)
    with pytest.raises(InterruptedError):
        analyze_interval(
            csv_path,
            metadata_path,
            None,
            None,
            cancelled=lambda: True,
        )

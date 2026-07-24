from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import TextIO

from hwlogger.models.log_session import LogSession
from hwlogger.models.sensor import Sensor, SensorType
from hwlogger.services.statistics_service import StatisticsService
from hwlogger.utils.atomic_write import atomic_write_json
from hwlogger.utils.time_utils import local_and_utc

SUMMARY_TYPES = {SensorType.TEMPERATURE, SensorType.POWER, SensorType.FAN}


class LoggingService:
    def __init__(self) -> None:
        self.session: LogSession | None = None
        self.sensors: list[Sensor] = []
        self.statistics = StatisticsService()
        self._stream: TextIO | None = None
        self._writer = None
        self._delimiter = ","
        self._flush_rows = 5
        self._monotonic_start = 0.0

    @property
    def active(self) -> bool:
        return self.session is not None

    def start(
        self, directory: Path, sensors: list[Sensor], delimiter: str = ",", flush_rows: int = 5
    ) -> LogSession:
        if self.active:
            raise RuntimeError("Recording is already active")
        if not sensors:
            raise ValueError("Select at least one sensor")
        directory.mkdir(parents=True, exist_ok=True)
        base = self._unique_base(directory)
        started = datetime.now().astimezone()
        self.session = LogSession(
            csv_path=base.with_suffix(".csv"),
            metadata_path=base.with_suffix(".json"),
            summary_path=base.with_name(f"{base.name}_summary.csv"),
            started_at=started,
        )
        self.sensors = list(sensors)
        self.statistics.reset([sensor.sensor_id for sensor in sensors])
        self._delimiter = delimiter
        self._flush_rows = max(1, flush_rows)
        self._stream = self.session.csv_path.open("x", newline="", encoding="utf-8")
        self._writer = csv.writer(self._stream, delimiter=delimiter)
        self._writer.writerow(
            ["timestamp_local", "timestamp_utc", "elapsed_seconds"]
            + [f"{sensor.name} [{sensor.unit}]" for sensor in sensors]
        )
        self._stream.flush()
        os.fsync(self._stream.fileno())
        import time

        self._monotonic_start = time.monotonic()
        self._write_metadata(None)
        return self.session

    def write_row(self, values: dict[str, float | str | None]) -> None:
        if not self.session or not self._writer or not self._stream:
            return
        import time

        elapsed = time.monotonic() - self._monotonic_start
        local, utc = local_and_utc()
        row: list[object] = [local, utc, f"{elapsed:.3f}"]
        for sensor in self.sensors:
            value = values.get(sensor.sensor_id)
            row.append("" if value is None else value)
            self.statistics.add(sensor.sensor_id, value)
        self._writer.writerow(row)
        self.session.rows += 1
        if self.session.rows % self._flush_rows == 0:
            self._stream.flush()

    def stop(self) -> LogSession | None:
        if not self.session:
            return None
        ended = datetime.now().astimezone()
        if self._stream:
            self._stream.flush()
            os.fsync(self._stream.fileno())
            self._stream.close()
        self._write_summary(ended)
        self._write_metadata(ended)
        completed = self.session
        self.session = None
        self.sensors = []
        self._stream = None
        self._writer = None
        return completed

    @staticmethod
    def _unique_base(directory: Path) -> Path:
        stamp = datetime.now().strftime("hwlog_%Y-%m-%d_%H-%M-%S")
        candidate = directory / stamp
        counter = 1
        while candidate.with_suffix(".csv").exists():
            candidate = directory / f"{stamp}_{counter}"
            counter += 1
        return candidate

    def _write_metadata(self, ended: datetime | None) -> None:
        assert self.session is not None
        data = {
            "format_version": 1,
            "started_at": self.session.started_at.isoformat(),
            "ended_at": ended.isoformat() if ended else None,
            "rows": self.session.rows,
            "csv_file": self.session.csv_path.name,
            "summary_file": self.session.summary_path.name if ended else None,
            "sensors": [
                {
                    "column": f"{sensor.name} [{sensor.unit}]",
                    "sensor_id": sensor.sensor_id,
                    "name": sensor.name,
                    "original_name": sensor.original_name,
                    "category": sensor.category.value,
                    "type": sensor.sensor_type.value,
                    "unit": sensor.unit,
                    "source": sensor.source,
                    "path": sensor.backend_id,
                }
                for sensor in self.sensors
            ],
        }
        atomic_write_json(self.session.metadata_path, data)

    def _write_summary(self, ended: datetime) -> None:
        assert self.session is not None
        duration = (ended - self.session.started_at).total_seconds()
        with self.session.summary_path.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, delimiter=self._delimiter)
            writer.writerow(
                [
                    "sensor_id", "name", "original_name", "category", "type", "source",
                    "started_at", "ended_at", "duration_seconds", "valid_count",
                    "minimum", "average", "maximum", "unit",
                ]
            )
            for sensor in self.sensors:
                if sensor.sensor_type not in SUMMARY_TYPES:
                    continue
                stats = self.statistics.values[sensor.sensor_id]
                writer.writerow(
                    [
                        sensor.sensor_id, sensor.name, sensor.original_name,
                        sensor.category.value, sensor.sensor_type.value, sensor.source,
                        self.session.started_at.isoformat(), ended.isoformat(), f"{duration:.3f}",
                        stats.count,
                        "" if stats.minimum is None else stats.minimum,
                        "" if stats.average is None else stats.average,
                        "" if stats.maximum is None else stats.maximum,
                        sensor.unit,
                    ]
                )
            stream.flush()
            os.fsync(stream.fileno())

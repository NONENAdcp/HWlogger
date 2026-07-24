from __future__ import annotations

import csv
import json
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from hwlogger.models.sensor import SensorType
from hwlogger.models.sensor_statistics import OnlineStatistics

ANALYSIS_TYPES = {
    SensorType.TEMPERATURE.value,
    SensorType.POWER.value,
    SensorType.FAN.value,
}


@dataclass(frozen=True, slots=True)
class LogSessionInfo:
    base_name: str
    csv_path: Path
    metadata_path: Path | None
    summary_path: Path | None
    started_at: datetime | None
    duration_seconds: float | None
    size_bytes: int
    rows: int | None
    sensor_count: int | None


@dataclass(frozen=True, slots=True)
class AnalysisRow:
    sensor_id: str
    name: str
    sensor_type: str
    unit: str
    count: int
    minimum: float | None
    average: float | None
    maximum: float | None
    duration_seconds: float


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def discover_sessions(directory: Path) -> list[LogSessionInfo]:
    if not directory.is_dir():
        return []
    sessions: list[LogSessionInfo] = []
    for csv_path in sorted(directory.glob("hwlog_*.csv"), reverse=True):
        if csv_path.name.endswith(("_summary.csv", "_interval_summary.csv")):
            continue
        base = csv_path.stem
        metadata_path = directory / f"{base}.json"
        summary_path = directory / f"{base}_summary.csv"
        metadata: dict[str, Any] = {}
        if metadata_path.is_file():
            try:
                metadata = _load_json(metadata_path)
            except (OSError, json.JSONDecodeError):
                metadata = {}
        started = None
        duration = None
        try:
            if metadata.get("started_at"):
                started = datetime.fromisoformat(str(metadata["started_at"]))
            if started and metadata.get("ended_at"):
                duration = (
                    datetime.fromisoformat(str(metadata["ended_at"])) - started
                ).total_seconds()
        except ValueError:
            started = None
            duration = None
        sessions.append(
            LogSessionInfo(
                base_name=base,
                csv_path=csv_path,
                metadata_path=metadata_path if metadata_path.is_file() else None,
                summary_path=summary_path if summary_path.is_file() else None,
                started_at=started,
                duration_seconds=duration,
                size_bytes=csv_path.stat().st_size,
                rows=(
                    int(metadata["rows"])
                    if isinstance(metadata.get("rows"), int)
                    else None
                ),
                sensor_count=(
                    len(metadata["sensors"])
                    if isinstance(metadata.get("sensors"), list)
                    else None
                ),
            )
        )
    return sessions


def read_summary(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        sample = stream.read(4096)
        stream.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        return list(csv.DictReader(stream, dialect=dialect))


def preview_csv(
    path: Path, first_count: int = 8, last_count: int = 8
) -> tuple[list[str], list[list[str]], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        sample = stream.read(4096)
        stream.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        reader = csv.reader(stream, dialect=dialect)
        header = next(reader, [])
        first: list[list[str]] = []
        last: deque[list[str]] = deque(maxlen=last_count)
        for row in reader:
            if len(first) < first_count:
                first.append(row)
            else:
                last.append(row)
        return header, first, list(last)


def analyze_interval(
    csv_path: Path,
    metadata_path: Path,
    start_seconds: float | None,
    end_seconds: float | None,
    progress: Callable[[int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> list[AnalysisRow]:
    metadata = _load_json(metadata_path)
    sensor_metadata = metadata.get("sensors", [])
    selected = [
        sensor
        for sensor in sensor_metadata
        if isinstance(sensor, dict) and sensor.get("type") in ANALYSIS_TYPES
    ]
    stats = {
        str(sensor["column"]): OnlineStatistics()
        for sensor in selected
        if sensor.get("column")
    }
    first_elapsed: float | None = None
    last_elapsed: float | None = None
    total_duration = float(metadata.get("duration_seconds") or 0)
    if not total_duration and metadata.get("started_at") and metadata.get("ended_at"):
        total_duration = (
            datetime.fromisoformat(str(metadata["ended_at"]))
            - datetime.fromisoformat(str(metadata["started_at"]))
        ).total_seconds()
    with csv_path.open(newline="", encoding="utf-8") as stream:
        sample = stream.read(4096)
        stream.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        reader = csv.DictReader(stream, dialect=dialect)
        for row_number, row in enumerate(reader, start=1):
            if cancelled and cancelled():
                raise InterruptedError("Анализ отменён")
            try:
                elapsed = float(row.get("elapsed_seconds", ""))
            except ValueError:
                continue
            if start_seconds is not None and elapsed < start_seconds:
                continue
            if end_seconds is not None and elapsed > end_seconds:
                break
            first_elapsed = elapsed if first_elapsed is None else first_elapsed
            last_elapsed = elapsed
            for column, accumulator in stats.items():
                raw = row.get(column, "")
                if raw not in ("", None):
                    try:
                        accumulator.add(float(raw))
                    except ValueError:
                        continue
            if progress and row_number % 500 == 0:
                denominator = end_seconds or total_duration
                progress(
                    min(99, int(elapsed / denominator * 100))
                    if denominator > 0
                    else 0
                )
    if progress:
        progress(100)
    duration = (
        max(0.0, last_elapsed - first_elapsed)
        if first_elapsed is not None and last_elapsed is not None
        else 0.0
    )
    result = []
    for sensor in selected:
        column = str(sensor.get("column", ""))
        accumulator = stats.get(column)
        if accumulator is None:
            continue
        result.append(
            AnalysisRow(
                sensor_id=str(sensor.get("sensor_id", "")),
                name=str(sensor.get("name", column)),
                sensor_type=str(sensor.get("type", "")),
                unit=str(sensor.get("unit", "")),
                count=accumulator.count,
                minimum=accumulator.minimum,
                average=accumulator.average,
                maximum=accumulator.maximum,
                duration_seconds=duration,
            )
        )
    return result

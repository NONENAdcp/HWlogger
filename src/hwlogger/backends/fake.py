from __future__ import annotations

import math
import time

from hwlogger.models.sensor import Sensor, SensorCategory, SensorType


class FakeSensorBackend:
    """Deterministic changing sensors enabled only by HWLOGGER_FAKE_SENSORS=1."""

    def __init__(self) -> None:
        self.started = time.monotonic()

    def _step(self) -> int:
        return int(time.monotonic() - self.started)

    def scan(self) -> list[Sensor]:
        definitions = [
            (
                "fake:temperature",
                "Тестовая температура CPU",
                SensorType.TEMPERATURE,
                "°C",
                lambda: 40.0 + self._step() % 20,
            ),
            (
                "fake:utilization",
                "Тестовая загрузка CPU",
                SensorType.UTILIZATION,
                "%",
                lambda: float((self._step() * 13) % 101),
            ),
            (
                "fake:frequency",
                "Тестовая частота CPU",
                SensorType.FREQUENCY,
                "MHz",
                lambda: 1800.0 + (self._step() % 8) * 200.0,
            ),
            (
                "fake:fan",
                "Тестовый вентилятор",
                SensorType.FAN,
                "RPM",
                lambda: 1000.0 + (self._step() % 10) * 100.0,
            ),
            (
                "fake:power",
                "Тестовая мощность CPU",
                SensorType.POWER,
                "W",
                lambda: round(20.0 + math.sin(self._step()) * 5.0, 2),
            ),
        ]
        return [
            Sensor(
                sensor_id=sensor_id,
                name=name,
                original_name=name,
                source="HWlogger fake",
                category=SensorCategory.SYSTEM,
                sensor_type=sensor_type,
                unit=unit,
                backend_id=sensor_id,
                reader=reader,
            )
            for sensor_id, name, sensor_type, unit, reader in definitions
        ]

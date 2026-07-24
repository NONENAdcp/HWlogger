from __future__ import annotations

import time
from pathlib import Path

from hwlogger.models.sensor import Sensor, SensorCategory, SensorType


class RaplPowerReader:
    def __init__(self, energy_path: Path, max_path: Path) -> None:
        self.energy_path = energy_path
        self.maximum = float(max_path.read_text().strip())
        self.previous_energy: float | None = None
        self.previous_time: float | None = None

    def __call__(self) -> float | None:
        energy = float(self.energy_path.read_text().strip())
        now = time.monotonic()
        if self.previous_energy is None or self.previous_time is None:
            self.previous_energy, self.previous_time = energy, now
            return None
        delta_time = now - self.previous_time
        delta_energy = energy - self.previous_energy
        if delta_energy < 0:
            delta_energy += self.maximum
        self.previous_energy, self.previous_time = energy, now
        if delta_time < 0.05 or delta_time > 30:
            return None
        return delta_energy / 1_000_000.0 / delta_time


class RaplBackend:
    def __init__(self, root: Path = Path("/sys/class/powercap")) -> None:
        self.root = root

    def scan(self) -> list[Sensor]:
        sensors = []
        for energy_path in self.root.glob("intel-rapl*/energy_uj"):
            domain = energy_path.parent
            maximum = domain / "max_energy_range_uj"
            name_path = domain / "name"
            if not maximum.is_file():
                continue
            name = name_path.read_text().strip() if name_path.is_file() else domain.name
            reader = RaplPowerReader(energy_path, maximum)
            sensors.append(
                Sensor(
                    sensor_id=f"rapl:{domain.name}",
                    name=f"Мощность {name}",
                    original_name=name,
                    source="Intel RAPL",
                    category=SensorCategory.POWER,
                    sensor_type=SensorType.POWER,
                    unit="W",
                    backend_id=str(energy_path),
                    reader=reader,
                )
            )
        return sensors

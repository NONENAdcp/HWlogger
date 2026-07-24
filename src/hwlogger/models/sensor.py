from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from hwlogger.models.sensor_statistics import OnlineStatistics


class SensorType(StrEnum):
    TEMPERATURE = "temperature"
    POWER = "power"
    FAN = "fan"
    VOLTAGE = "voltage"
    CURRENT = "current"
    ENERGY = "energy"
    UTILIZATION = "utilization"
    FREQUENCY = "frequency"
    MEMORY = "memory"
    LOAD = "load"
    STATE = "state"
    OTHER = "other"


class SensorCategory(StrEnum):
    CPU = "CPU"
    NVIDIA_GPU = "NVIDIA GPU"
    THINKPAD_EC = "ThinkPad EC"
    FAN = "Fan"
    POWER = "Power"
    MEMORY = "Memory"
    SYSTEM = "System"
    OTHER = "Other"


SensorReader = Callable[[], float | str | None]


@dataclass(slots=True)
class Sensor:
    sensor_id: str
    name: str
    original_name: str
    source: str
    category: SensorCategory
    sensor_type: SensorType
    unit: str
    backend_id: str
    reader: SensorReader = field(repr=False)
    label: str = ""
    value: float | str | None = None
    available: bool = True
    last_success: datetime | None = None
    last_error: str = ""
    selected_for_log: bool = False
    selected_for_graph: bool = False
    statistics: OnlineStatistics = field(default_factory=OnlineStatistics)

    def read(self) -> float | str | None:
        try:
            value = self.reader()
            if value is None:
                raise ValueError("no value")
            self.value = value
            self.available = True
            self.last_error = ""
            self.last_success = datetime.now().astimezone()
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                self.statistics.add(float(value))
            return value
        except Exception as exc:
            self.value = None
            self.available = False
            self.last_error = str(exc)
            return None

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SensorValue:
    sensor_id: str
    timestamp: datetime
    value: float | str | None

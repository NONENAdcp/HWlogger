from abc import ABC, abstractmethod

from hwlogger.models.sensor import Sensor


class SensorBackend(ABC):
    @abstractmethod
    def scan(self) -> list[Sensor]:
        """Discover sensors without modifying the host."""

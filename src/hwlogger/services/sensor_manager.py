from __future__ import annotations

import logging
import os

from hwlogger.backends.cpu import CpuBackend
from hwlogger.backends.fake import FakeSensorBackend
from hwlogger.backends.hwmon import HwmonBackend
from hwlogger.backends.memory import MemoryBackend
from hwlogger.backends.nvidia import NvidiaBackend
from hwlogger.backends.rapl import RaplBackend
from hwlogger.models.sensor import Sensor
from hwlogger.services.config_service import AppConfig

LOGGER = logging.getLogger(__name__)


class SensorManager:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.nvidia = NvidiaBackend(config.allow_nvidia_wake)
        if os.environ.get("HWLOGGER_FAKE_SENSORS") == "1":
            self.backends = [FakeSensorBackend()]
            LOGGER.info("HWLOGGER_FAKE_SENSORS=1: using deterministic fake sensors")
        else:
            self.backends = [
                HwmonBackend(),
                CpuBackend(),
                MemoryBackend(),
                RaplBackend(),
                self.nvidia,
            ]
        self.sensors: dict[str, Sensor] = {}

    def scan(self) -> list[Sensor]:
        discovered: dict[str, Sensor] = {}
        for backend in self.backends:
            try:
                for sensor in backend.scan():
                    previous = self.sensors.get(sensor.sensor_id)
                    if previous is not None:
                        sensor.statistics = previous.statistics
                        sensor.value = previous.value
                    sensor.name = self.config.custom_names.get(sensor.sensor_id, sensor.name)
                    sensor.selected_for_log = sensor.sensor_id in self.config.selected_sensors
                    discovered[sensor.sensor_id] = sensor
            except Exception:
                LOGGER.exception("Sensor backend scan failed: %s", type(backend).__name__)
        for sensor_id, old in self.sensors.items():
            if sensor_id not in discovered:
                old.available = False
                old.last_error = "Sensor disappeared"
                discovered[sensor_id] = old
        self.sensors = discovered
        return list(discovered.values())

    def read_all(self) -> dict[str, float | str | None]:
        return {sensor.sensor_id: sensor.read() for sensor in self.sensors.values()}

    def shutdown(self) -> None:
        self.nvidia.shutdown()

from __future__ import annotations

from contextlib import suppress

from hwlogger.models.sensor import Sensor, SensorCategory, SensorType


class NvidiaBackend:
    def __init__(self, allow_wake: bool = False) -> None:
        self.allow_wake = allow_wake
        self._nvml = None

    def scan(self) -> list[Sensor]:
        if not self.allow_wake:
            return []
        try:
            import pynvml

            pynvml.nvmlInit()
            self._nvml = pynvml
            count = pynvml.nvmlDeviceGetCount()
        except Exception:
            return []
        sensors: list[Sensor] = []
        for index in range(count):
            handle = self._nvml.nvmlDeviceGetHandleByIndex(index)
            definitions = [
                (
                    "temperature",
                    "Температура GPU",
                    "GPU Temperature",
                    SensorType.TEMPERATURE,
                    "°C",
                    lambda h=handle: float(
                        self._nvml.nvmlDeviceGetTemperature(
                            h, self._nvml.NVML_TEMPERATURE_GPU
                        )
                    ),
                ),
                (
                    "utilization",
                    "Загрузка GPU",
                    "GPU Utilization",
                    SensorType.UTILIZATION,
                    "%",
                    lambda h=handle: float(
                        self._nvml.nvmlDeviceGetUtilizationRates(h).gpu
                    ),
                ),
                (
                    "memory_utilization",
                    "Загрузка контроллера памяти GPU",
                    "GPU Memory Utilization",
                    SensorType.UTILIZATION,
                    "%",
                    lambda h=handle: float(
                        self._nvml.nvmlDeviceGetUtilizationRates(h).memory
                    ),
                ),
                (
                    "power",
                    "Мощность GPU",
                    "GPU Power",
                    SensorType.POWER,
                    "W",
                    lambda h=handle: self._nvml.nvmlDeviceGetPowerUsage(h) / 1000.0,
                ),
                (
                    "vram_used",
                    "Использовано VRAM",
                    "GPU Memory Used",
                    SensorType.MEMORY,
                    "MiB",
                    lambda h=handle: self._nvml.nvmlDeviceGetMemoryInfo(h).used / 2**20,
                ),
                (
                    "fan",
                    "Вентилятор GPU",
                    "GPU Fan",
                    SensorType.FAN,
                    "%",
                    lambda h=handle: float(self._nvml.nvmlDeviceGetFanSpeed(h)),
                ),
            ]
            for key, name, original_name, kind, unit, reader in definitions:
                sensors.append(
                    Sensor(
                        sensor_id=f"nvidia:{index}:{key}",
                        name=name if count == 1 else f"GPU {index + 1}: {name}",
                        original_name=original_name,
                        source="NVML",
                        category=SensorCategory.NVIDIA_GPU,
                        sensor_type=kind,
                        unit=unit,
                        backend_id=f"gpu:{index}:{key}",
                        reader=reader,
                    )
                )
        return sensors

    def shutdown(self) -> None:
        if self._nvml is not None:
            with suppress(Exception):
                self._nvml.nvmlShutdown()
            self._nvml = None

from __future__ import annotations

import os
import time

import psutil

from hwlogger.models.sensor import Sensor, SensorCategory, SensorType


def _sensor(
    sensor_id: str,
    name: str,
    original_name: str,
    sensor_type: SensorType,
    unit: str,
    reader,
) -> Sensor:
    return Sensor(
        sensor_id=sensor_id,
        name=name,
        original_name=original_name,
        source="psutil",
        category=SensorCategory.CPU if sensor_type != SensorType.LOAD else SensorCategory.SYSTEM,
        sensor_type=sensor_type,
        unit=unit,
        backend_id=sensor_id,
        reader=reader,
    )


class CpuBackend:
    def scan(self) -> list[Sensor]:
        sensors = [
            _sensor(
                "cpu:total",
                "Загрузка CPU",
                "CPU Total Usage",
                SensorType.UTILIZATION,
                "%",
                psutil.cpu_percent,
            ),
            _sensor(
                "cpu:frequency:average",
                "Средняя частота CPU",
                "CPU Average Frequency",
                SensorType.FREQUENCY,
                "MHz",
                lambda: float(psutil.cpu_freq().current),
            ),
        ]
        for index in range(psutil.cpu_count(logical=True) or 0):
            sensors.append(
                _sensor(
                    f"cpu:thread:{index}",
                    f"Загрузка потока {index + 1}",
                    f"CPU Core {index} Usage",
                    SensorType.UTILIZATION,
                    "%",
                    lambda i=index: float(psutil.cpu_percent(percpu=True)[i]),
                )
            )
        for index, period in enumerate((1, 5, 15)):
            sensors.append(
                _sensor(
                    f"system:load:{period}",
                    f"Средняя нагрузка за {period} мин",
                    f"Load Average {period}m",
                    SensorType.LOAD,
                    "",
                    lambda i=index: float(os.getloadavg()[i]),
                )
            )
        sensors.append(
            _sensor(
                "system:uptime",
                "Время работы системы",
                "Uptime",
                SensorType.OTHER,
                "s",
                lambda: max(0.0, time.time() - psutil.boot_time()),
            )
        )
        return sensors

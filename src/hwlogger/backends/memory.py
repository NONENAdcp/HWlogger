import psutil

from hwlogger.models.sensor import Sensor, SensorCategory, SensorType


class MemoryBackend:
    def scan(self) -> list[Sensor]:
        definitions = [
            (
                "memory:used",
                "Использовано RAM",
                "Memory Used",
                "MiB",
                lambda: psutil.virtual_memory().used / 2**20,
            ),
            (
                "memory:available",
                "Доступно RAM",
                "Memory Available",
                "MiB",
                lambda: psutil.virtual_memory().available / 2**20,
            ),
            (
                "memory:percent",
                "Загрузка RAM",
                "Memory Usage",
                "%",
                lambda: psutil.virtual_memory().percent,
            ),
            (
                "swap:used",
                "Использовано Swap",
                "Swap Used",
                "MiB",
                lambda: psutil.swap_memory().used / 2**20,
            ),
            (
                "swap:percent",
                "Загрузка Swap",
                "Swap Usage",
                "%",
                lambda: psutil.swap_memory().percent,
            ),
        ]
        return [
            Sensor(
                sensor_id=sensor_id,
                name=name,
                original_name=original_name,
                source="psutil",
                category=SensorCategory.MEMORY,
                sensor_type=SensorType.MEMORY,
                unit=unit,
                backend_id=sensor_id,
                reader=reader,
            )
            for sensor_id, name, original_name, unit, reader in definitions
        ]

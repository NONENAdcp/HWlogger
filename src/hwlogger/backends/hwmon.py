from __future__ import annotations

import hashlib
import re
from pathlib import Path

from hwlogger.backends.base import SensorBackend
from hwlogger.models.sensor import Sensor, SensorCategory, SensorType
from hwlogger.utils.units import convert_hwmon

INPUT_PATTERN = re.compile(r"^(temp|fan|power|energy|in|curr|freq)(\d+)_(input|average)$")
TYPE_MAP = {
    "temp": (SensorType.TEMPERATURE, "°C"),
    "fan": (SensorType.FAN, "RPM"),
    "power": (SensorType.POWER, "W"),
    "energy": (SensorType.ENERGY, "J"),
    "in": (SensorType.VOLTAGE, "V"),
    "curr": (SensorType.CURRENT, "A"),
    "freq": (SensorType.FREQUENCY, "MHz"),
}


def stable_sensor_id(device_path: Path, attribute: str) -> str:
    resolved = str(device_path.resolve(strict=False))
    digest = hashlib.sha256(f"{resolved}\0{attribute}".encode()).hexdigest()[:16]
    return f"hwmon:{digest}"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _category(device_name: str, sensor_type: SensorType) -> SensorCategory:
    lowered = device_name.lower()
    if sensor_type == SensorType.FAN:
        return SensorCategory.FAN
    if "thinkpad" in lowered:
        return SensorCategory.THINKPAD_EC
    if lowered in {"coretemp", "k10temp", "zenpower"}:
        return SensorCategory.CPU
    if sensor_type in {SensorType.POWER, SensorType.ENERGY, SensorType.CURRENT}:
        return SensorCategory.POWER
    return SensorCategory.OTHER


def automatic_sensor_name(
    device_name: str,
    prefix: str,
    index: str,
    label: str,
    sensor_type: SensorType,
) -> str:
    """Create a conservative Russian name while retaining raw names separately."""
    lowered = device_name.casefold()
    normalized_label = label.casefold()
    number = int(index)
    if sensor_type == SensorType.FAN:
        return f"Вентилятор {number}"
    if "thinkpad" in lowered:
        if normalized_label == "cpu":
            return "Температура CPU"
        if normalized_label == "gpu":
            return "Температура GPU"
        return f"Датчик EC {prefix}{index}"
    if lowered == "coretemp":
        if normalized_label.startswith("package"):
            return "Температура CPU"
        if normalized_label.startswith("core"):
            try:
                core_number = int(normalized_label.rsplit(maxsplit=1)[-1]) + 1
            except ValueError:
                core_number = number - 1
            return f"Температура ядра {core_number}"
    if lowered == "nvme" and sensor_type == SensorType.TEMPERATURE:
        if normalized_label == "composite":
            return "Температура NVMe"
        return f"Температура NVMe: {label}" if label else f"Датчик NVMe temp{index}"
    if "iwlwifi" in lowered and sensor_type == SensorType.TEMPERATURE:
        return "Температура Wi-Fi"
    if lowered == "acpitz" and sensor_type == SensorType.TEMPERATURE:
        return "Температура ACPI"
    type_names = {
        SensorType.TEMPERATURE: "Температура",
        SensorType.POWER: "Мощность",
        SensorType.VOLTAGE: "Напряжение",
        SensorType.CURRENT: "Ток",
        SensorType.ENERGY: "Энергия",
        SensorType.FREQUENCY: "Частота",
    }
    base = type_names.get(sensor_type, sensor_type.value)
    subject = label or device_name
    return f"{base}: {subject}" if subject else f"{base} {index}"


class HwmonBackend(SensorBackend):
    def __init__(self, root: Path = Path("/sys/class/hwmon")) -> None:
        self.root = root

    def scan(self) -> list[Sensor]:
        sensors: list[Sensor] = []
        for hwmon in sorted(self.root.glob("hwmon*")):
            try:
                device_name = _read_text(hwmon / "name")
            except OSError:
                continue
            device_path = hwmon.resolve(strict=False)
            for path in sorted(hwmon.iterdir()):
                match = INPUT_PATTERN.match(path.name)
                if not match or not path.is_file():
                    continue
                prefix, index, suffix = match.groups()
                average_exists = (hwmon / f"power{index}_average").exists()
                if prefix == "power" and suffix == "input" and average_exists:
                    continue
                sensor_type, unit = TYPE_MAP[prefix]
                label_path = hwmon / f"{prefix}{index}_label"
                try:
                    label = _read_text(label_path) if label_path.is_file() else ""
                except OSError:
                    label = ""
                raw_name = f"{prefix}{index}_{suffix}"
                display = automatic_sensor_name(
                    device_name, prefix, index, label, sensor_type
                )

                def reader(value_path: Path = path, kind: SensorType = sensor_type) -> float:
                    return convert_hwmon(_read_text(value_path), kind)

                sensors.append(
                    Sensor(
                        sensor_id=stable_sensor_id(device_path, path.name),
                        name=display,
                        original_name=raw_name,
                        label=label,
                        source=f"hwmon:{device_name}",
                        category=_category(device_name, sensor_type),
                        sensor_type=sensor_type,
                        unit=unit,
                        backend_id=str(path.resolve(strict=False)),
                        reader=reader,
                    )
                )
        return sensors

from decimal import ROUND_HALF_UP, Decimal

from hwlogger.models.sensor import SensorType


def convert_hwmon(raw: str, sensor_type: SensorType) -> float:
    value = float(raw.strip())
    divisors = {
        SensorType.TEMPERATURE: 1_000.0,
        SensorType.POWER: 1_000_000.0,
        SensorType.ENERGY: 1_000_000.0,
        SensorType.VOLTAGE: 1_000.0,
        SensorType.CURRENT: 1_000.0,
        SensorType.FREQUENCY: 1_000_000.0,
        SensorType.FAN: 1.0,
    }
    return value / divisors.get(sensor_type, 1.0)


def format_value(value: float | str | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value)
    quantum = Decimal(1).scaleb(-decimals)
    rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    return f"{rounded:.{decimals}f}"

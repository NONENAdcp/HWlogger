import pytest

from hwlogger.models.sensor import SensorType
from hwlogger.utils.units import convert_hwmon, format_value


@pytest.mark.parametrize(
    ("raw", "kind", "expected"),
    [
        ("42000", SensorType.TEMPERATURE, 42.0),
        ("15000000", SensorType.POWER, 15.0),
        ("1230000", SensorType.ENERGY, 1.23),
        ("1200", SensorType.VOLTAGE, 1.2),
        ("2500", SensorType.CURRENT, 2.5),
        ("0", SensorType.FAN, 0.0),
    ],
)
def test_hwmon_conversion(raw, kind, expected):
    assert convert_hwmon(raw, kind) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(62.49, "62"), (62.5, "63"), (-2.5, "-3"), (3180.4, "3180"), (0.0, "0")],
)
def test_gui_value_uses_half_up_rounding(value, expected):
    assert format_value(value, 0) == expected

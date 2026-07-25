import pytest

from hwlogger.ui.temperature_indication import TemperatureLevel, temperature_level


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (69.9, TemperatureLevel.NORMAL),
        (70.0, TemperatureLevel.YELLOW),
        (80.0, TemperatureLevel.ORANGE),
        (85.0, TemperatureLevel.RED),
        (90.0, TemperatureLevel.BRIGHT_RED),
        (95.0, TemperatureLevel.DARK_RED),
    ],
)
def test_temperature_levels_at_boundaries(value, expected):
    assert temperature_level(value) == expected


def test_temperature_level_rises_immediately_and_falls_with_hysteresis():
    assert temperature_level(80.0, TemperatureLevel.YELLOW) == TemperatureLevel.ORANGE
    assert temperature_level(79.0, TemperatureLevel.ORANGE) == TemperatureLevel.ORANGE
    assert temperature_level(78.1, TemperatureLevel.ORANGE) == TemperatureLevel.ORANGE
    assert temperature_level(78.0, TemperatureLevel.ORANGE) == TemperatureLevel.YELLOW

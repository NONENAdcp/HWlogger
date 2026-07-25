from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class TemperatureLevel(IntEnum):
    NORMAL = 0
    YELLOW = 1
    ORANGE = 2
    RED = 3
    BRIGHT_RED = 4
    DARK_RED = 5


@dataclass(frozen=True, slots=True)
class TemperatureProfile:
    """Temperature thresholds for a device group."""

    thresholds: tuple[float, float, float, float, float] = (
        70.0,
        80.0,
        85.0,
        90.0,
        95.0,
    )
    hysteresis: float = 2.0

    def level_for(self, value: float) -> TemperatureLevel:
        level = TemperatureLevel.NORMAL
        for index, threshold in enumerate(self.thresholds, start=1):
            if value < threshold:
                break
            level = TemperatureLevel(index)
        return level

    def level_with_hysteresis(
        self,
        value: float,
        previous: TemperatureLevel = TemperatureLevel.NORMAL,
    ) -> TemperatureLevel:
        target = self.level_for(value)
        if target >= previous or previous == TemperatureLevel.NORMAL:
            return target
        previous_lower_bound = self.thresholds[int(previous) - 1]
        if value > previous_lower_bound - self.hysteresis:
            return previous
        return target


DEFAULT_TEMPERATURE_PROFILE = TemperatureProfile()


def temperature_level(
    value: float,
    previous: TemperatureLevel = TemperatureLevel.NORMAL,
    profile: TemperatureProfile = DEFAULT_TEMPERATURE_PROFILE,
) -> TemperatureLevel:
    return profile.level_with_hysteresis(value, previous)

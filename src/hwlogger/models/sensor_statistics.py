from dataclasses import dataclass


@dataclass(slots=True)
class OnlineStatistics:
    count: int = 0
    minimum: float | None = None
    maximum: float | None = None
    mean: float = 0.0

    def add(self, value: float | None) -> None:
        if value is None:
            return
        number = float(value)
        self.count += 1
        self.minimum = number if self.minimum is None else min(self.minimum, number)
        self.maximum = number if self.maximum is None else max(self.maximum, number)
        self.mean += (number - self.mean) / self.count

    @property
    def average(self) -> float | None:
        return self.mean if self.count else None

    def reset(self) -> None:
        self.count = 0
        self.minimum = None
        self.maximum = None
        self.mean = 0.0

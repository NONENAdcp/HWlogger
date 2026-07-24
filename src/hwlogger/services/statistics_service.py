from hwlogger.models.sensor_statistics import OnlineStatistics


class StatisticsService:
    def __init__(self) -> None:
        self.values: dict[str, OnlineStatistics] = {}

    def reset(self, sensor_ids: list[str]) -> None:
        self.values = {sensor_id: OnlineStatistics() for sensor_id in sensor_ids}

    def add(self, sensor_id: str, value: float | str | None) -> None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self.values.setdefault(sensor_id, OnlineStatistics()).add(float(value))

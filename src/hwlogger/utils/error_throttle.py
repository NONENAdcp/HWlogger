import logging
import time


class ErrorThrottle:
    def __init__(self, interval: float = 60.0) -> None:
        self.interval = interval
        self._last: dict[str, float] = {}

    def log(self, logger: logging.Logger, key: str, message: str) -> None:
        now = time.monotonic()
        if now - self._last.get(key, 0.0) >= self.interval:
            logger.warning("%s", message)
            self._last[key] = now

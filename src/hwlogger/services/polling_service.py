from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from hwlogger.services.sensor_manager import SensorManager

LOGGER = logging.getLogger(__name__)


class PollWorker(QObject):
    values_ready = Signal(dict)
    stopped = Signal()

    def __init__(self, manager: SensorManager, interval_ms: int) -> None:
        super().__init__()
        self.manager = manager
        self.interval_ms = interval_ms
        self.timer: QTimer | None = None
        self._previous_values: dict[str, float | str | None] = {}
        self._stopping = False

    @Slot()
    def start(self) -> None:
        LOGGER.info(
            "Polling worker start; current_thread=%s worker_thread=%s",
            QThread.currentThread().objectName(),
            self.thread().objectName(),
        )
        self.timer = QTimer(self)
        self.timer.setInterval(self.interval_ms)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        LOGGER.info(
            "Polling timer started; active=%s interval_ms=%d timer_thread=%s",
            self.timer.isActive(),
            self.timer.interval(),
            self.timer.thread().objectName(),
        )
        self.poll()

    @Slot()
    def poll(self) -> None:
        if self._stopping or QThread.currentThread().isInterruptionRequested():
            return
        LOGGER.debug("Polling cycle begin")
        values = self.manager.read_all()
        changed = sum(
            1
            for sensor_id, value in values.items()
            if self._previous_values.get(sensor_id, object()) != value
        )
        self._previous_values = dict(values)
        LOGGER.debug(
            "Polling cycle complete; sensors=%d changed=%d; emitting values_ready",
            len(values),
            changed,
        )
        self.values_ready.emit(values)

    @Slot()
    def stop(self) -> None:
        LOGGER.info("Polling worker stop")
        self._stopping = True
        if self.timer:
            self.timer.stop()
            self.timer.deleteLater()
            self.timer = None
        self.stopped.emit()
        QThread.currentThread().quit()


class PollingService(QObject):
    values_ready = Signal(dict)
    request_stop = Signal()

    def __init__(self, manager: SensorManager, interval_ms: int) -> None:
        super().__init__()
        self.thread = QThread()
        self.thread.setObjectName("HWloggerPollingThread")
        self.worker = PollWorker(manager, interval_ms)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start)
        self.thread.started.connect(
            lambda: LOGGER.info("Polling QThread started; running=%s", self.thread.isRunning())
        )
        self.worker.values_ready.connect(self.values_ready)
        self.worker.values_ready.connect(
            lambda values: LOGGER.debug(
                "PollingService received worker signal; sensors=%d", len(values)
            )
        )
        self.request_stop.connect(self.worker.stop)
        self.worker.stopped.connect(self.worker.deleteLater)

    def start(self) -> None:
        LOGGER.info(
            "Calling QThread.start; worker_alive=%s thread_alive=%s",
            self.worker is not None,
            self.thread is not None,
        )
        self.thread.start()

    def stop(self, timeout_ms: int = 700) -> bool:
        if self.thread.isRunning():
            self.request_stop.emit()
            if self.thread.wait(timeout_ms):
                return True
            LOGGER.warning(
                "Polling thread did not stop within %d ms; requesting interruption",
                timeout_ms,
            )
            self.thread.requestInterruption()
            self.thread.quit()
            if self.thread.wait(100):
                return True
            LOGGER.error("Polling thread required forced termination")
            self.thread.terminate()
            return self.thread.wait(100)
        return True

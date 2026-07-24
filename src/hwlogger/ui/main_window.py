from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from hwlogger.services.config_service import AppConfig, ConfigService
from hwlogger.services.logging_service import LoggingService
from hwlogger.services.polling_service import PollingService
from hwlogger.services.sensor_manager import SensorManager
from hwlogger.ui.sensors_tab import SensorsTab
from hwlogger.ui.settings_tab import SettingsTab
from hwlogger.widgets.recording_panel import RecordingPanel

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, config_service: ConfigService, config: AppConfig) -> None:
        super().__init__()
        self.config_service = config_service
        self.config = config
        self.manager = SensorManager(config)
        self.sensors = self.manager.scan()
        self.logger = LoggingService()
        self.latest_values: dict[str, float | str | None] = {}
        self.record_started = 0.0
        self.setWindowTitle("HWlogger 0.1.0")
        self.resize(config.window_width, config.window_height)
        self.panel = RecordingPanel()
        self.sensors_tab = SensorsTab()
        self.sensors_tab.set_sensors(self.sensors, 0)
        self.settings_tab = SettingsTab(config)
        tabs = QTabWidget()
        tabs.addTab(self.sensors_tab, "Датчики")
        tabs.addTab(QLabel("Живые графики появятся на этапе 2."), "Графики")
        tabs.addTab(QLabel("Просмотр и анализ логов появятся на этапе 2."), "Логи")
        tabs.addTab(self.settings_tab, "Настройки")
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.panel)
        layout.addWidget(tabs)
        self.setCentralWidget(central)
        self.panel.start_requested.connect(self.start_recording)
        self.panel.stop_requested.connect(self.stop_recording)
        self.sensors_tab.selection_changed.connect(self._selection_changed)
        self.sensors_tab.rescan_requested.connect(self.rescan)
        self.settings_tab.save_requested.connect(self.save_settings)
        self.polling = PollingService(self.manager, config.ui_interval_ms)
        self.polling.values_ready.connect(self._values_ready)
        self.polling.start()
        self.log_timer = QTimer(self)
        self.log_timer.setInterval(config.logging_interval_ms)
        self.log_timer.timeout.connect(self._log_row)
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(250)
        self.status_timer.timeout.connect(self._update_record_status)
        self.status_timer.start()
        self._selection_changed()

    def _selection_changed(self) -> None:
        selected = [sensor for sensor in self.sensors if sensor.selected_for_log]
        self.panel.set_selected(len(selected))

    def _values_ready(self, values: dict) -> None:
        if QThread.currentThread() != self.thread():
            raise RuntimeError("Sensor GUI update attempted outside the main Qt thread")
        LOGGER.debug(
            "MainWindow received values_ready in GUI thread; sensors=%d", len(values)
        )
        self.latest_values = values
        changed_rows = self.sensors_tab.update_values()
        LOGGER.debug("Sensor table updated; changed_rows=%d", changed_rows)

    def start_recording(self) -> None:
        selected = [sensor for sensor in self.sensors if sensor.selected_for_log]
        try:
            session = self.logger.start(
                Path(self.config.log_directory),
                selected,
                self.config.csv_delimiter,
                self.config.flush_rows,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Не удалось начать запись", str(exc))
            return
        self.record_started = time.monotonic()
        self.panel.path.setText(f"Файл: {session.csv_path}")
        self.panel.set_recording(True)
        self.log_timer.start()
        self._log_row()

    def _log_row(self) -> None:
        self.logger.write_row(self.latest_values)

    def stop_recording(self) -> None:
        self.log_timer.stop()
        try:
            session = self.logger.stop()
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка завершения записи", str(exc))
            return
        self.panel.set_recording(False)
        if session:
            self.statusBar().showMessage(f"Сохранено: {session.csv_path}", 10_000)

    def _update_record_status(self) -> None:
        if not self.logger.session:
            return
        elapsed = int(time.monotonic() - self.record_started)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.panel.elapsed.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
        self.panel.rows.setText(f"Строк: {self.logger.session.rows}")

    def rescan(self) -> None:
        self.sensors = self.manager.scan()
        self.sensors_tab.set_sensors(self.sensors, 0)
        self._selection_changed()

    def save_settings(self) -> None:
        self.config.log_directory = self.settings_tab.log_directory.text()
        self.config.ui_interval_ms = self.settings_tab.ui_interval.value()
        self.config.logging_interval_ms = self.settings_tab.log_interval.value()
        self.config.flush_rows = self.settings_tab.flush_rows.currentData()
        self.config.csv_delimiter = self.settings_tab.delimiter.currentData()
        self.config.decimals = 0
        self.config.allow_nvidia_wake = self.settings_tab.allow_nvidia.isChecked()
        self.config.selected_sensors = [
            sensor.sensor_id for sensor in self.sensors if sensor.selected_for_log
        ]
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        try:
            self.config_service.save(self.config)
            self.statusBar().showMessage(
                "Настройки сохранены. Интервалы применятся после перезапуска.", 5000
            )
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка сохранения настроек", str(exc))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.logger.active:
            result = QMessageBox.question(
                self,
                "Идёт запись",
                "Остановить запись, создать сводку и закрыть HWlogger?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.stop_recording()
            if self.logger.active:
                event.ignore()
                return
        self.save_settings()
        self.polling.stop()
        self.manager.shutdown()
        event.accept()

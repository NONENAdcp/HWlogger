from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from hwlogger import __version__
from hwlogger.services.config_service import AppConfig, ConfigService
from hwlogger.services.logging_service import LoggingService
from hwlogger.services.polling_service import PollingService
from hwlogger.services.sensor_manager import SensorManager
from hwlogger.ui.dialogs.about_dialog import AboutDialog
from hwlogger.ui.graphs_tab import GraphsTab
from hwlogger.ui.logs_tab import LogsTab
from hwlogger.ui.sensors_tab import SensorsTab
from hwlogger.ui.settings_tab import SettingsTab
from hwlogger.ui.tray import TrayController
from hwlogger.widgets.recording_panel import RecordingPanel

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_service: ConfigService,
        config: AppConfig,
        tray_available: bool | None = None,
    ) -> None:
        super().__init__()
        self.config_service = config_service
        self.config = config
        self.manager = SensorManager(config)
        self.sensors = self.manager.scan()
        self.logger = LoggingService()
        self.latest_values: dict[str, float | str | None] = {}
        self.record_started = 0.0
        self._closing = False
        self._exit_requested = False
        self._shutdown_complete = False
        if tray_available is None:
            tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray_controller = TrayController(self) if tray_available else None
        app = QApplication.instance()
        if self.tray_controller is not None and app is not None:
            app.setQuitOnLastWindowClosed(False)
        self.setWindowTitle(f"HWlogger {__version__}")
        self.resize(config.window_width, config.window_height)
        self.panel = RecordingPanel()
        self.sensors_tab = SensorsTab(
            config.technical_columns_visible, config.sensor_column_widths
        )
        self.sensors_tab.set_sensors(self.sensors, 0)
        self.settings_tab = SettingsTab(config, tray_available)
        self.logs_tab = LogsTab(Path(config.log_directory))
        self.graphs_tab = GraphsTab()
        self.graphs_tab.set_sensors(self.sensors)
        tabs = QTabWidget()
        tabs.addTab(self.sensors_tab, "Датчики")
        tabs.addTab(self.graphs_tab, "Графики")
        tabs.addTab(self.logs_tab, "Логи")
        tabs.addTab(self.settings_tab, "Настройки")
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.panel)
        layout.addWidget(tabs)
        self.setCentralWidget(central)
        help_menu = self.menuBar().addMenu("Справка")
        about_action = help_menu.addAction("О программе")
        about_action.triggered.connect(self.show_about)
        self.panel.start_requested.connect(self.start_recording)
        self.panel.stop_requested.connect(self.stop_recording)
        self.sensors_tab.selection_changed.connect(self._selection_changed)
        self.sensors_tab.rescan_requested.connect(self.rescan)
        self.settings_tab.save_requested.connect(self.save_settings)
        if self.tray_controller is not None:
            self.tray_controller.exit_requested.connect(self.request_exit)
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
        if self._closing:
            return
        if QThread.currentThread() != self.thread():
            raise RuntimeError("Sensor GUI update attempted outside the main Qt thread")
        LOGGER.debug(
            "MainWindow received values_ready in GUI thread; sensors=%d", len(values)
        )
        self.latest_values = values
        changed_rows = self.sensors_tab.update_values()
        self.graphs_tab.update_values(values)
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
        if not self._closing:
            self.panel.set_recording(False)
        if session and not self._closing:
            self.statusBar().showMessage(f"Сохранено: {session.csv_path}", 10_000)
            self.logs_tab.refresh()

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
        self.graphs_tab.set_sensors(self.sensors)
        self._selection_changed()

    def save_settings(self, refresh_logs: bool = True) -> None:
        self.config.log_directory = self.settings_tab.log_directory.text()
        self.config.ui_interval_ms = self.settings_tab.ui_interval.value()
        self.config.logging_interval_ms = self.settings_tab.log_interval.value()
        self.config.flush_rows = self.settings_tab.flush_rows.currentData()
        self.config.csv_delimiter = self.settings_tab.delimiter.currentData()
        self.config.decimals = 0
        self.config.allow_nvidia_wake = self.settings_tab.allow_nvidia.isChecked()
        self.config.close_to_tray = self.settings_tab.close_to_tray.isChecked()
        if refresh_logs:
            self.logs_tab.set_directory(Path(self.config.log_directory))
        self.config.selected_sensors = [
            sensor.sensor_id for sensor in self.sensors if sensor.selected_for_log
        ]
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        self.config.technical_columns_visible = (
            self.sensors_tab.technical_columns.isChecked()
        )
        self.config.sensor_column_widths = self.sensors_tab.table.column_widths()
        try:
            self.config_service.save(self.config)
            self.statusBar().showMessage(
                "Настройки сохранены. Интервалы применятся после перезапуска.", 5000
            )
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка сохранения настроек", str(exc))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._shutdown_complete:
            event.accept()
            return
        if (
            not self._exit_requested
            and self.tray_controller is not None
            and self.settings_tab.close_to_tray.isChecked()
        ):
            event.ignore()
            self.tray_controller.hide_window()
            self.tray_controller.notify_hidden_once()
            return
        if self._closing:
            event.ignore()
            return
        if self.logger.active:
            result = QMessageBox.question(
                self,
                "Идёт запись",
                "Остановить запись, создать сводку и закрыть HWlogger?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                self._exit_requested = False
                event.ignore()
                return
        shutdown_started = time.perf_counter()
        self._closing = True
        LOGGER.info("Shutdown started")

        stage_started = time.perf_counter()
        self.log_timer.stop()
        self.status_timer.stop()
        LOGGER.info(
            "Shutdown stage timers: %.3f s", time.perf_counter() - stage_started
        )

        if self.logger.active:
            stage_started = time.perf_counter()
            self.stop_recording()
            LOGGER.info(
                "Shutdown stage recording: %.3f s",
                time.perf_counter() - stage_started,
            )
            if self.logger.active:
                self._closing = False
                self._exit_requested = False
                event.ignore()
                return

        stage_started = time.perf_counter()
        try:
            self.polling.values_ready.disconnect(self._values_ready)
        except RuntimeError:
            LOGGER.debug("Polling signal was already disconnected")
        polling_stopped = self.polling.stop(timeout_ms=700)
        LOGGER.info(
            "Shutdown stage polling: %.3f s (stopped=%s)",
            time.perf_counter() - stage_started,
            polling_stopped,
        )

        stage_started = time.perf_counter()
        self.manager.shutdown()
        LOGGER.info(
            "Shutdown stage backends: %.3f s", time.perf_counter() - stage_started
        )

        stage_started = time.perf_counter()
        self.save_settings(refresh_logs=False)
        LOGGER.info(
            "Shutdown stage config: %.3f s", time.perf_counter() - stage_started
        )
        if self.tray_controller is not None:
            self.tray_controller.shutdown()
            app = QApplication.instance()
            if app is not None:
                app.setQuitOnLastWindowClosed(True)
        self._shutdown_complete = True
        LOGGER.info("Shutdown complete: %.3f s", time.perf_counter() - shutdown_started)
        event.accept()

    def request_exit(self) -> None:
        if self._exit_requested or self._shutdown_complete:
            return
        self._exit_requested = True
        self.close()

    def show_about(self) -> None:
        AboutDialog(Path(self.config.log_directory), self).exec()

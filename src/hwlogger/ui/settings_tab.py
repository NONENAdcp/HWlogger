from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from hwlogger.services.config_service import AppConfig


class SettingsTab(QWidget):
    save_requested = Signal()

    def __init__(self, config: AppConfig, tray_available: bool = True) -> None:
        super().__init__()
        self.log_directory = QLineEdit(config.log_directory)
        browse = QPushButton("Обзор…")
        directory_row = QHBoxLayout()
        directory_row.addWidget(self.log_directory)
        directory_row.addWidget(browse)
        self.ui_interval = QSpinBox()
        self.ui_interval.setRange(100, 60_000)
        self.ui_interval.setValue(config.ui_interval_ms)
        self.ui_interval.setSuffix(" мс")
        self.log_interval = QSpinBox()
        self.log_interval.setRange(100, 60_000)
        self.log_interval.setValue(config.logging_interval_ms)
        self.log_interval.setSuffix(" мс")
        self.flush_rows = QComboBox()
        for value in (1, 5, 10):
            self.flush_rows.addItem(f"Каждые {value} строк", value)
        self.flush_rows.setCurrentIndex(max(0, self.flush_rows.findData(config.flush_rows)))
        self.delimiter = QComboBox()
        self.delimiter.addItem("Запятая", ",")
        self.delimiter.addItem("Точка с запятой", ";")
        self.delimiter.setCurrentIndex(max(0, self.delimiter.findData(config.csv_delimiter)))
        self.allow_nvidia = QCheckBox()
        self.allow_nvidia.setChecked(config.allow_nvidia_wake)
        self.close_to_tray = QCheckBox()
        self.close_to_tray.setChecked(config.close_to_tray)
        self.close_to_tray.setEnabled(tray_available)
        if not tray_available:
            self.close_to_tray.setToolTip("Системный трей недоступен")
        save = QPushButton("Сохранить настройки")
        form = QFormLayout(self)
        form.addRow("Каталог логов", directory_row)
        form.addRow("Интервал интерфейса", self.ui_interval)
        form.addRow("Интервал записи", self.log_interval)
        form.addRow("Flush", self.flush_rows)
        form.addRow("CSV-разделитель", self.delimiter)
        form.addRow("Разрешить пробуждать NVIDIA GPU", self.allow_nvidia)
        form.addRow("Сворачивать в трей при закрытии окна", self.close_to_tray)
        form.addRow(save)
        browse.clicked.connect(self._browse)
        save.clicked.connect(self.save_requested)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Каталог логов", self.log_directory.text())
        if path:
            self.log_directory.setText(path)

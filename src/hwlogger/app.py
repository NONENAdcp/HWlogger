from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from hwlogger.services.config_service import ConfigService
from hwlogger.ui.main_window import MainWindow
from hwlogger.utils.paths import state_dir


def configure_logging() -> None:
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=directory / "hwlogger.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("HWlogger")
    app.setOrganizationName("HWlogger")
    config_service = ConfigService()
    config = config_service.load()
    window = MainWindow(config_service, config)
    window.show()
    if config_service.warning:
        QMessageBox.warning(window, "Конфигурация восстановлена", config_service.warning)
    return app.exec()

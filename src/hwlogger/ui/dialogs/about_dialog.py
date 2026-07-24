from __future__ import annotations

import platform
from pathlib import Path

import PySide6
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from hwlogger import PROJECT_URL, __version__
from hwlogger.utils.paths import config_path


class AboutDialog(QDialog):
    def __init__(self, log_directory: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О программе HWlogger")
        details = QLabel(
            "<h2>HWlogger</h2>"
            f"<p>Версия {__version__}</p>"
            "<p>GPL-3.0-or-later</p>"
            f"<p>Python: {platform.python_version()}<br>"
            f"Qt: {qVersion()}<br>"
            f"PySide6: {PySide6.__version__}</p>"
            f"<p>Конфигурация:<br><code>{config_path()}</code></p>"
            f"<p>Каталог логов:<br><code>{log_directory}</code></p>"
            f'<p><a href="{PROJECT_URL}">GitHub project</a></p>'
        )
        details.setOpenExternalLinks(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(details)
        layout.addWidget(buttons)

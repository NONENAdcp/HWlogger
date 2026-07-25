from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QStyle,
    QSystemTrayIcon,
)


class TrayController(QObject):
    exit_requested = Signal()

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        self.window = window
        self._close_notification_shown = False
        self._trigger_timer = QElapsedTimer()
        icon_path = Path(__file__).resolve().parent.parent / "resources" / "hwlogger.svg"
        icon = QIcon(str(icon_path))
        if icon.isNull():
            icon = window.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray = QSystemTrayIcon(icon, window)
        self.tray.setToolTip("HWlogger")
        self.menu = QMenu(window)
        self.show_action = QAction("Показать HWlogger", self.menu)
        self.hide_action = QAction("Скрыть HWlogger", self.menu)
        self.exit_action = QAction("Выход", self.menu)
        self.menu.addAction(self.show_action)
        self.menu.addAction(self.hide_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)
        self.tray.setContextMenu(self.menu)
        self.show_action.triggered.connect(self.show_window)
        self.hide_action.triggered.connect(self.hide_window)
        self.exit_action.triggered.connect(self.exit_requested)
        self.tray.activated.connect(self._activated)
        self.tray.show()

    def show_window(self) -> None:
        if self.window.isMinimized():
            self.window.showNormal()
        else:
            self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def hide_window(self) -> None:
        self.window.hide()

    def notify_hidden_once(self) -> None:
        if self._close_notification_shown:
            return
        self._close_notification_shown = True
        self.tray.showMessage(
            "HWlogger",
            "HWlogger продолжает работать в системном трее",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def shutdown(self) -> None:
        self.tray.hide()

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._trigger_timer.invalidate()
            self.show_window()
            return
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            self._trigger_timer.invalidate()
            return
        app = QApplication.instance()
        interval = app.doubleClickInterval() if app is not None else 400
        if self._trigger_timer.isValid() and self._trigger_timer.elapsed() <= interval:
            self._trigger_timer.invalidate()
            self.show_window()
        else:
            self._trigger_timer.start()

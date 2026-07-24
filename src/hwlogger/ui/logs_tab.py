from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hwlogger.services.log_reader import (
    LogSessionInfo,
    discover_sessions,
    read_summary,
)
from hwlogger.ui.dialogs.interval_analysis_dialog import IntervalAnalysisDialog
from hwlogger.ui.dialogs.log_preview_dialog import LogPreviewDialog


def _size_text(size: int) -> str:
    if size >= 1024**2:
        return f"{size / 1024**2:.1f} MiB"
    if size >= 1024:
        return f"{size / 1024:.1f} KiB"
    return f"{size} B"


class SummaryDialog(QDialog):
    def __init__(self, path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Сводка — {path.name}")
        self.resize(850, 520)
        rows = read_summary(path)
        headers = ["Название", "Минимум", "Среднее", "Максимум", "Единица", "Измерений"]
        keys = ["name", "minimum", "average", "maximum", "unit", "valid_count"]
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            for column, key in enumerate(keys):
                table.setItem(row_index, column, QTableWidgetItem(row.get(key, "")))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(table)
        layout.addWidget(buttons)


class LogsTab(QWidget):
    def __init__(self, directory: Path) -> None:
        super().__init__()
        self.directory = directory
        self.sessions: list[LogSessionInfo] = []
        self.directory_label = QLabel()
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Дата и время", "Длительность", "Размер", "Строк", "Датчиков", "Summary"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        refresh = QPushButton("Обновить")
        summary = QPushButton("Показать сводку")
        interval = QPushButton("Выбрать промежуток")
        preview = QPushButton("Предпросмотр CSV")
        open_csv = QPushButton("Открыть CSV")
        open_directory = QPushButton("Открыть каталог")
        delete = QPushButton("Удалить сессию")
        controls = QHBoxLayout()
        for button in (
            refresh,
            summary,
            interval,
            preview,
            open_csv,
            open_directory,
            delete,
        ):
            controls.addWidget(button)
        controls.addStretch()
        layout = QVBoxLayout(self)
        layout.addWidget(self.directory_label)
        layout.addLayout(controls)
        layout.addWidget(self.table)
        refresh.clicked.connect(self.refresh)
        summary.clicked.connect(self.show_summary)
        interval.clicked.connect(self.analyze_interval)
        preview.clicked.connect(self.preview)
        open_csv.clicked.connect(self.open_csv)
        open_directory.clicked.connect(self.open_directory)
        delete.clicked.connect(self.delete_session)
        self.table.doubleClicked.connect(lambda _index: self.show_summary())
        self.refresh()

    def set_directory(self, directory: Path) -> None:
        self.directory = directory
        self.refresh()

    def refresh(self) -> None:
        self.directory_label.setText(f"Каталог: {self.directory}")
        self.sessions = discover_sessions(self.directory)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.sessions))
        for row, session in enumerate(self.sessions):
            started = (
                session.started_at.strftime("%Y-%m-%d %H:%M:%S")
                if session.started_at
                else session.base_name.removeprefix("hwlog_").replace("_", " ")
            )
            values = [
                started,
                (
                    f"{session.duration_seconds:.1f} с"
                    if session.duration_seconds is not None
                    else "—"
                ),
                _size_text(session.size_bytes),
                str(session.rows) if session.rows is not None else "—",
                (
                    str(session.sensor_count)
                    if session.sensor_count is not None
                    else "—"
                ),
                "Есть" if session.summary_path else "Нет",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, session)
                self.table.setItem(row, column, item)
        self.table.setSortingEnabled(True)
        if self.sessions:
            self.table.selectRow(0)

    def selected_session(self) -> LogSessionInfo | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        return value if isinstance(value, LogSessionInfo) else None

    def _require_session(self) -> LogSessionInfo | None:
        session = self.selected_session()
        if session is None:
            QMessageBox.information(self, "Сессия не выбрана", "Выберите сессию в таблице")
        return session

    def show_summary(self) -> None:
        session = self._require_session()
        if session is None:
            return
        if session.summary_path is None:
            QMessageBox.information(self, "Нет сводки", "Для этой сессии summary не найден")
            return
        try:
            SummaryDialog(session.summary_path, self).exec()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Ошибка чтения сводки", str(exc))

    def analyze_interval(self) -> None:
        session = self._require_session()
        if session is not None:
            IntervalAnalysisDialog(session, self).exec()

    def preview(self) -> None:
        session = self._require_session()
        if session is None:
            return
        try:
            LogPreviewDialog(session.csv_path, self).exec()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Ошибка предпросмотра", str(exc))

    def open_csv(self) -> None:
        session = self._require_session()
        if session is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(session.csv_path)))

    def open_directory(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.directory)))

    def delete_session(self) -> None:
        session = self._require_session()
        if session is None:
            return
        answer = QMessageBox.question(
            self,
            "Удалить сессию",
            "Удалить CSV, JSON-метаданные и summary выбранной сессии?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        paths = [session.csv_path, session.metadata_path, session.summary_path]
        try:
            for path in paths:
                if path is not None:
                    path.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка удаления", str(exc))
        self.refresh()

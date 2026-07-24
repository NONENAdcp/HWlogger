from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from hwlogger.services.log_reader import AnalysisRow, LogSessionInfo, analyze_interval


class AnalysisWorker(QObject):
    progress = Signal(int)
    finished = Signal(list)
    failed = Signal(str)
    done = Signal()

    def __init__(
        self,
        session: LogSessionInfo,
        start_seconds: float | None,
        end_seconds: float | None,
    ) -> None:
        super().__init__()
        self.session = session
        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            if self.session.metadata_path is None:
                raise ValueError("Для анализа необходим JSON-файл метаданных")
            rows = analyze_interval(
                self.session.csv_path,
                self.session.metadata_path,
                self.start_seconds,
                self.end_seconds,
                self.progress.emit,
                lambda: self._cancelled,
            )
            self.finished.emit(rows)
        except InterruptedError:
            self.failed.emit("Анализ отменён")
        except (OSError, ValueError, csv.Error) as exc:
            self.failed.emit(str(exc))
        finally:
            self.done.emit()

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True


class AnalysisResultDialog(QDialog):
    def __init__(self, rows: list[AnalysisRow], suggested_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.rows = rows
        self.suggested_path = suggested_path
        self.setWindowTitle("Результат анализа")
        self.resize(850, 520)
        headers = [
            "Название", "Минимум", "Среднее", "Максимум", "Единица",
            "Измерений", "Длительность, с",
        ]
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            values = [
                row.name,
                "" if row.minimum is None else str(row.minimum),
                "" if row.average is None else str(row.average),
                "" if row.maximum is None else str(row.maximum),
                row.unit,
                str(row.count),
                f"{row.duration_seconds:.3f}",
            ]
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(value))
        export = QPushButton("Экспортировать CSV")
        close = QPushButton("Закрыть")
        controls = QHBoxLayout()
        controls.addWidget(export)
        controls.addStretch()
        controls.addWidget(close)
        layout = QVBoxLayout(self)
        layout.addWidget(table)
        layout.addLayout(controls)
        export.clicked.connect(self._export)
        close.clicked.connect(self.accept)

    def _export(self) -> None:
        selected, _ = QFileDialog.getSaveFileName(
            self, "Экспортировать результат", str(self.suggested_path), "CSV (*.csv)"
        )
        if not selected:
            return
        with Path(selected).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                [
                    "sensor_id", "name", "type", "minimum", "average", "maximum",
                    "unit", "valid_count", "duration_seconds",
                ]
            )
            for row in self.rows:
                writer.writerow(
                    [
                        row.sensor_id, row.name, row.sensor_type, row.minimum,
                        row.average, row.maximum, row.unit, row.count,
                        row.duration_seconds,
                    ]
                )


class IntervalAnalysisDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, session: LogSessionInfo, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.thread: QThread | None = None
        self.worker: AnalysisWorker | None = None
        self.setWindowTitle(f"Анализ промежутка — {session.csv_path.name}")
        self.resize(520, 260)
        self.mode = QComboBox()
        self.mode.addItem("Вся запись", None)
        for minutes in (1, 5, 10, 30, 60):
            self.mode.addItem(f"Последние {minutes} мин", minutes)
        self.mode.addItem("Произвольный промежуток", "manual")
        maximum = max(0.0, session.duration_seconds or 0.0)
        self.start_value = QDoubleSpinBox()
        self.start_value.setRange(0, maximum)
        self.start_value.setSuffix(" с")
        self.end_value = QDoubleSpinBox()
        self.end_value.setRange(0, maximum)
        self.end_value.setValue(maximum)
        self.end_value.setSuffix(" с")
        self.start_value.setEnabled(False)
        self.end_value.setEnabled(False)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.message = QLabel("")
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        form = QFormLayout()
        form.addRow("Промежуток", self.mode)
        form.addRow("Начало", self.start_value)
        form.addRow("Конец", self.end_value)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.progress)
        layout.addWidget(self.message)
        layout.addWidget(self.buttons)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.buttons.accepted.connect(self._start)
        self.buttons.rejected.connect(self._cancel_or_close)

    def _mode_changed(self) -> None:
        manual = self.mode.currentData() == "manual"
        self.start_value.setEnabled(manual)
        self.end_value.setEnabled(manual)

    def _bounds(self) -> tuple[float | None, float | None]:
        mode = self.mode.currentData()
        duration = self.session.duration_seconds or 0.0
        if mode == "manual":
            return self.start_value.value(), self.end_value.value()
        if isinstance(mode, int):
            return max(0.0, duration - mode * 60), None
        return None, None

    def _start(self) -> None:
        start, end = self._bounds()
        if end is not None and start is not None and end < start:
            self.message.setText("Конец промежутка должен быть позже начала")
            return
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.message.setText(f"Анализируется {self.session.csv_path.name}")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.thread = QThread(self)
        self.worker = AnalysisWorker(self.session, start, end)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.cancel_requested.connect(
            self.worker.cancel, Qt.ConnectionType.DirectConnection
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._show_result)
        self.worker.failed.connect(self.message.setText)
        self.worker.done.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._finished)
        self.thread.start()

    def _show_result(self, rows: list[AnalysisRow]) -> None:
        path = self.session.csv_path.with_name(
            f"{self.session.base_name}_interval_summary.csv"
        )
        AnalysisResultDialog(rows, path, self).exec()

    def _finished(self) -> None:
        self.progress.setVisible(False)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        self.thread = None
        self.worker = None

    def _cancel_or_close(self) -> None:
        if self.thread and self.thread.isRunning():
            self.cancel_requested.emit()
            self.message.setText("Отмена…")
        else:
            self.reject()

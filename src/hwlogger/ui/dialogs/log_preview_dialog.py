from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from hwlogger.services.log_reader import preview_csv


class LogPreviewDialog(QDialog):
    def __init__(self, path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Предпросмотр — {path.name}")
        self.resize(1100, 650)
        header, first, last = preview_csv(path)
        table = QTableWidget(0, len(header))
        table.setHorizontalHeaderLabels(header)
        rows: list[list[str] | None] = list(first)
        if last:
            rows.append(None)
            rows.extend(last)
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            if row is None:
                if header:
                    item = QTableWidgetItem("…")
                    table.setItem(row_index, 0, item)
                    table.setSpan(row_index, 0, 1, len(header))
                continue
            for column, value in enumerate(row[: len(header)]):
                table.setItem(row_index, column, QTableWidgetItem(value))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Заголовок, первые и последние строки файла"))
        layout.addWidget(table)
        layout.addWidget(buttons)

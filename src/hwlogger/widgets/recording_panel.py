from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RecordingPanel(QWidget):
    start_requested = Signal()
    stop_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.start_button = QPushButton("Начать запись")
        self.stop_button = QPushButton("Остановить запись")
        self.stop_button.setEnabled(False)
        self.status = QLabel("● Запись не идёт")
        self.elapsed = QLabel("00:00:00")
        self.rows = QLabel("Строк: 0")
        self.selected = QLabel("Выбрано датчиков: 0")
        self.path = QLabel("Файл: —")
        self.warning = QLabel("Выберите хотя бы один датчик")
        self.warning.setStyleSheet("color: #d98c00")
        top = QHBoxLayout()
        for widget in (
            self.start_button,
            self.stop_button,
            self.status,
            self.elapsed,
            self.rows,
            self.selected,
            self.warning,
        ):
            top.addWidget(widget)
        top.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.path)
        self.start_button.clicked.connect(self.start_requested)
        self.stop_button.clicked.connect(self.stop_requested)

    def set_recording(self, recording: bool) -> None:
        self.start_button.setEnabled(not recording)
        self.stop_button.setEnabled(recording)
        self.status.setText("● Запись идёт" if recording else "● Запись не идёт")
        self.status.setStyleSheet("color: #d33" if recording else "")

    def set_selected(self, count: int) -> None:
        self.selected.setText(f"Выбрано датчиков: {count}")
        self.warning.setVisible(count == 0)

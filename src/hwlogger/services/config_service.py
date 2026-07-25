from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from hwlogger.utils.atomic_write import atomic_write_json
from hwlogger.utils.paths import config_path, default_log_dir


@dataclass(slots=True)
class AppConfig:
    log_directory: str = field(default_factory=lambda: str(default_log_dir()))
    ui_interval_ms: int = 1000
    logging_interval_ms: int = 1000
    flush_rows: int = 5
    csv_delimiter: str = ","
    decimals: int = 2
    theme: str = "system"
    allow_nvidia_wake: bool = False
    close_to_tray: bool = True
    show_unavailable: bool = True
    selected_sensors: list[str] = field(default_factory=list)
    custom_names: dict[str, str] = field(default_factory=dict)
    window_width: int = 1280
    window_height: int = 760
    technical_columns_visible: bool = False
    sensor_column_widths: dict[str, int] = field(default_factory=dict)


class ConfigService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_path()
        self.warning = ""

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            raw: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
            allowed = set(AppConfig.__dataclass_fields__)
            return AppConfig(**{key: value for key, value in raw.items() if key in allowed})
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = self.path.with_name(f"{self.path.name}.corrupt-{stamp}")
            try:
                shutil.copy2(self.path, backup)
            except OSError:
                backup = self.path
            self.warning = f"Повреждённая конфигурация сохранена как {backup}: {exc}"
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        atomic_write_json(self.path, asdict(config))

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from hwlogger.utils.atomic_write import atomic_write_json
from hwlogger.utils.paths import config_path, default_log_dir

DEFAULT_UI_INTERVAL_MS = 1000
MIN_POLLING_INTERVAL_MS = 100
MAX_POLLING_INTERVAL_MS = 60_000
MAIN_TAB_IDS = ("sensors", "graphs", "logs", "settings")


@dataclass(slots=True)
class AppConfig:
    log_directory: str = field(default_factory=lambda: str(default_log_dir()))
    ui_interval_ms: int = DEFAULT_UI_INTERVAL_MS
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
    window_geometry: str = ""
    window_maximized: bool = False
    active_tab: str = "sensors"
    selected_graph_sensors: list[str] = field(default_factory=list)
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
            raw: Any = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise TypeError("configuration root must be an object")
            return _config_from_mapping(raw)
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


def valid_polling_interval(value: object) -> int:
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and MIN_POLLING_INTERVAL_MS <= value <= MAX_POLLING_INTERVAL_MS
    ):
        return value
    return DEFAULT_UI_INTERVAL_MS


def _string_ids(value: object, limit: int | None = None) -> list[str] | None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return None
    unique = list(dict.fromkeys(value))
    return unique[:limit] if limit is not None else unique


def _config_from_mapping(raw: dict[str, Any]) -> AppConfig:
    defaults = AppConfig()
    values: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in AppConfig.__dataclass_fields__:
            continue
        default = getattr(defaults, key)
        if isinstance(default, bool):
            if isinstance(value, bool):
                values[key] = value
        elif isinstance(default, int):
            if isinstance(value, int) and not isinstance(value, bool):
                values[key] = value
        elif isinstance(default, str):
            if isinstance(value, str):
                values[key] = value
        elif isinstance(default, list):
            parsed = _string_ids(
                value, limit=8 if key == "selected_graph_sensors" else None
            )
            if parsed is not None:
                values[key] = parsed
        elif isinstance(default, dict) and isinstance(value, dict):
            values[key] = value

    values["ui_interval_ms"] = valid_polling_interval(
        values.get("ui_interval_ms", defaults.ui_interval_ms)
    )
    if values.get("active_tab", defaults.active_tab) not in MAIN_TAB_IDS:
        values["active_tab"] = defaults.active_tab
    geometry = values.get("window_geometry", defaults.window_geometry)
    if len(geometry) > 65_536:
        values["window_geometry"] = defaults.window_geometry
    for dimension in ("window_width", "window_height"):
        if not 200 <= values.get(dimension, getattr(defaults, dimension)) <= 10_000:
            values[dimension] = getattr(defaults, dimension)
    return AppConfig(**values)

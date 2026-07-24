import os
from pathlib import Path


def _xdg(env: str, fallback: Path) -> Path:
    value = os.environ.get(env)
    return Path(value).expanduser() if value else fallback


def config_path() -> Path:
    return _xdg("XDG_CONFIG_HOME", Path.home() / ".config") / "hwlogger" / "config.json"


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", Path.home() / ".local/state") / "hwlogger"


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", Path.home() / ".cache") / "hwlogger"


def default_log_dir() -> Path:
    return Path.home() / "HWLogs"

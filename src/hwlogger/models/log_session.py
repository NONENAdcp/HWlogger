from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class LogSession:
    csv_path: Path
    metadata_path: Path
    summary_path: Path
    started_at: datetime
    rows: int = 0

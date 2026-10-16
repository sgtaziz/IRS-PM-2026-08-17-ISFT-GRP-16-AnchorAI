"""Admin data operations (W42): replace the raw CSV and rebuild everything in the background."""

import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from anchorai import pipeline
from anchorai.config import get_settings
from anchorai.knowledge.reload import sync_graph
from anchorai.scenario.build import load_kaggle
from anchorai.scenario.tables import SchemaError

RAW_NAME = "gym_churn_us.csv"


@dataclass
class BuildStatus:
    state: str = "idle"
    seed: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


_status = BuildStatus()
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def status() -> dict:
    return asdict(_status)


def start_rebuild(seed: int) -> dict:
    """Start `pipeline.run` in a thread; raises RuntimeError if one is already running."""
    global _status
    with _lock:
        if _status.state == "running":
            raise RuntimeError("A rebuild is already running")
        _status = BuildStatus("running", seed, _now())

    def work() -> None:
        global _status
        try:
            pipeline.run(seed)
            # Admin roster edits live in SQLite on top of the rebuilt tables; reload the KG and its
            # rule facts so they match. Never raises: a down graph is shown as stale on its page.
            sync_graph()
            _status = BuildStatus("done", seed, _status.started_at, _now())
        except Exception as exc:  # noqa: BLE001  a thread must record any failure for the page
            _status = BuildStatus("failed", seed, _status.started_at, _now(), str(exc))

    threading.Thread(target=work, daemon=True).start()
    return status()


def raw_dir() -> Path:
    return get_settings().anchorai_data_dir / "raw"


def replace_raw(content: bytes) -> int:
    """Validate an uploaded Kaggle CSV and make it the only raw file; returns its row count."""
    with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            rows = len(load_kaggle(Path(tmp.name)))
        except SchemaError as e:
            raise ValueError(str(e).replace(Path(tmp.name).name, "Uploaded CSV")) from None
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError):
            raise ValueError("Uploaded file is not a readable CSV") from None
    if rows < 100:
        raise ValueError(f"Expected the full member table, got {rows} rows")
    directory = raw_dir()
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob("*.csv"):
        old.unlink()
    (directory / RAW_NAME).write_bytes(content)
    return rows


def raw_info() -> dict | None:
    files = sorted(raw_dir().glob("*.csv"))
    if not files:
        return None
    stat = files[0].stat()
    modified = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(timespec="seconds")
    return {"name": files[0].name, "bytes": stat.st_size, "modified_at": modified}

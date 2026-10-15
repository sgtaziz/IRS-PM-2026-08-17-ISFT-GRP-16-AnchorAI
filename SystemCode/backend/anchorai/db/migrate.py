from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

import anchorai
from anchorai.config import get_settings
from anchorai.db.session import make_engine

BACKEND_DIR = Path(anchorai.__file__).resolve().parent.parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def alembic_config(url: str | None = None) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", url or get_settings().anchorai_db_url)
    return cfg


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)


def upgrade(url: str | None = None, revision: str = "head") -> None:
    cfg = alembic_config(url)
    _ensure_sqlite_dir(cfg.get_main_option("sqlalchemy.url"))
    command.upgrade(cfg, revision)


def downgrade(url: str | None = None, revision: str = "base") -> None:
    command.downgrade(alembic_config(url), revision)


def heads(url: str | None = None) -> list[str]:
    return list(ScriptDirectory.from_config(alembic_config(url)).get_heads())


def current_revision(url: str | None = None) -> str | None:
    engine = make_engine(url or get_settings().anchorai_db_url)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()

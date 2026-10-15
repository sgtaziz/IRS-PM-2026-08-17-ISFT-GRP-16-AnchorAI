from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlmodel import SQLModel

from anchorai.db import migrate
from anchorai.db.session import make_engine


def test_single_head():
    assert len(migrate.heads()) == 1


def test_round_trip_and_no_drift(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    migrate.upgrade(url)
    migrate.downgrade(url)
    migrate.upgrade(url)
    assert migrate.current_revision(url) == migrate.heads()[0]

    engine = make_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(
            MigrationContext.configure(conn, opts={"compare_type": True}), SQLModel.metadata
        )
    engine.dispose()
    assert diff == [], "models changed without a migration"

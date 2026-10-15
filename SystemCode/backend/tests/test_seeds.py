from sqlmodel import Session, func, select

from anchorai.db.models import RuleVersion, User
from anchorai.db.seeds import run_seeds


def test_seeds_are_idempotent(engine):
    with Session(engine) as session:
        run_seeds(session, ("base", "demo"))
        assert session.exec(select(func.count()).select_from(User)).one() == 4
        assert session.exec(select(func.count()).select_from(RuleVersion)).one() == 1

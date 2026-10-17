"""Base seed layer: demo users, the rule base as version 1, offers, roster and constraints.

bcrypt salts are random by design, so hashes differ between runs. Idempotency comes from
creating only the missing users (existing ones are kept, so a changed ANCHORAI_DEMO_PASSWORD
needs `anchorai db reset`), and ANCHORAI_SEED governs everything else.
"""

import random

from sqlmodel import Session, select

from anchorai import catalog
from anchorai.auth.security import hash_password
from anchorai.config import get_settings
from anchorai.db.models import RuleVersion, User
from anchorai.reasoning.engine import load_rule_files
from anchorai.reasoning.versions import dump_rules

DEMO_USERS: list[tuple[str, str, str]] = [
    ("admin", "admin", "Alex Admin"),
    ("manager", "manager", "Morgan Manager"),
    ("staff1", "staff", "Sam Staff"),
    ("staff2", "staff", "Jordan Staff"),
]


def seed(session: Session, rng: random.Random) -> None:
    password = get_settings().anchorai_demo_password
    existing = set(session.exec(select(User.username)).all())
    for username, role, full_name in DEMO_USERS:
        if username not in existing:
            session.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                    full_name=full_name,
                )
            )

    if session.exec(select(RuleVersion).where(RuleVersion.version == 1)).first() is None:
        session.add(
            RuleVersion(
                version=1,
                yaml_text=dump_rules(load_rule_files()),
                note="Seeded rule base",
                is_active=True,
            )
        )

    session.flush()
    catalog.seed(session, rng)

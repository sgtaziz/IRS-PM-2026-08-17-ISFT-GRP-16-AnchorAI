"""Base seed layer: demo users and the rule base as version 1.

bcrypt salts are random by design, so hashes differ between runs; idempotency comes from
upserting by username, and ANCHORAI_SEED governs everything else.
"""

import random
from pathlib import Path

from sqlmodel import Session, select

import anchorai.reasoning
from anchorai.auth.security import hash_password
from anchorai.config import get_settings
from anchorai.db.models import RuleVersion, User

RULES_DIR = Path(anchorai.reasoning.__file__).parent / "rules"

DEMO_USERS: list[tuple[str, str, str]] = [
    ("admin", "admin", "Alex Admin"),
    ("manager", "manager", "Morgan Manager"),
    ("staff1", "staff", "Sam Staff"),
    ("staff2", "staff", "Jordan Staff"),
]


def rules_yaml() -> str:
    return "\n".join(p.read_text() for p in sorted(RULES_DIR.glob("*.yaml")))


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
            RuleVersion(version=1, yaml_text=rules_yaml(), note="Seeded rule base", is_active=True)
        )

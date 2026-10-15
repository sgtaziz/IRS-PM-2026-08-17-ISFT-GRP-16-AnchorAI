import random

from sqlmodel import Session


def seed(session: Session, rng: random.Random) -> None:
    """Stream B adds the approved past week (plan, assignments, outcomes, audit) here."""

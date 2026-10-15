import random
from collections.abc import Callable, Sequence

from sqlmodel import Session

from anchorai.config import get_settings
from anchorai.db.seeds import base, demo

SeedLayer = Callable[[Session, random.Random], None]

LAYERS: dict[str, SeedLayer] = {"base": base.seed, "demo": demo.seed}


def run_seeds(session: Session, layers: Sequence[str] = ("base",), seed: int | None = None) -> None:
    """Apply seed layers in order. Each layer is idempotent, so re-running is a no-op."""
    rng = random.Random(get_settings().anchorai_seed if seed is None else seed)
    for name in layers:
        LAYERS[name](session, rng)
        session.commit()

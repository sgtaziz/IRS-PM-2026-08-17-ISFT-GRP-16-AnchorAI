from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import bcrypt
import jwt

from anchorai.config import get_settings
from anchorai.db.models import User

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@lru_cache
def _dummy_hash() -> str:
    return hash_password("timing-equaliser")


def burn_password_check(password: str) -> None:
    """Spend the same bcrypt time as a real check, so unknown usernames aren't revealed."""
    verify_password(password, _dummy_hash())


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        # bcrypt 5 rejects passwords over 72 bytes instead of truncating them.
        return False


def create_access_token(user: User) -> str:
    s = get_settings()
    claims = {
        "sub": user.username,
        "uid": user.id,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(minutes=s.anchorai_jwt_ttl_minutes),
    }
    return jwt.encode(claims, s.anchorai_jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        get_settings().anchorai_jwt_secret,
        algorithms=[ALGORITHM],
        options={"require": ["exp", "sub", "uid"]},
    )

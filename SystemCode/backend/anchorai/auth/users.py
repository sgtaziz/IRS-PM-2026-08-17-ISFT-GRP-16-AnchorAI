"""User administration (W43): create, edit, deactivate and reset passwords, with audit."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, func, select

from anchorai.auth.schemas import UserOut
from anchorai.auth.security import MAX_PASSWORD_BYTES, hash_password
from anchorai.db.audit import record_audit
from anchorai.db.models import Role, User


class UserRow(UserOut):
    created_at: datetime


def _fits_bcrypt(password: str) -> str:
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
    return password


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9._-]{3,40}$")
    full_name: str = Field(default="", max_length=100)
    role: Role
    password: str = Field(min_length=8)

    _password_size = field_validator("password")(_fits_bcrypt)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=100)
    role: Role | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8)

    _password_size = field_validator("password")(_fits_bcrypt)


class UserConflict(ValueError):
    pass


class UserRuleViolation(ValueError):
    pass


class UnknownUser(LookupError):
    pass


def _view(user: User) -> dict[str, Any]:
    """What goes into the audit log: never the password hash."""
    return {
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }


def list_users(session: Session) -> list[UserRow]:
    rows = session.exec(select(User).order_by(User.username)).all()
    return [UserRow.model_validate(u, from_attributes=True) for u in rows]


def _get(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise UnknownUser(f"No user {user_id}")
    return user


def create_user(session: Session, actor: User, body: UserCreate) -> UserRow:
    if session.exec(select(User).where(User.username == body.username)).first() is not None:
        raise UserConflict(f"Username {body.username} is taken")
    user = User(
        username=body.username,
        full_name=body.full_name.strip(),
        role=body.role,
        password_hash=hash_password(body.password),
    )
    session.add(user)
    session.flush()
    record_audit(session, actor, "user_create", "user", str(user.id), after=_view(user))
    session.commit()
    return UserRow.model_validate(user, from_attributes=True)


def _active_admins(session: Session) -> int:
    return session.exec(
        select(func.count()).select_from(User).where(User.role == "admin", User.is_active)
    ).one()


def update_user(session: Session, actor: User, user_id: int, body: UserUpdate) -> UserRow:
    user = _get(session, user_id)
    before = _view(user)
    demoting = body.role is not None and body.role != "admin" and user.role == "admin"
    deactivating = body.is_active is False and user.is_active
    if (
        user.role == "admin"
        and user.is_active
        and (demoting or deactivating)
        and _active_admins(session) <= 1
    ):
        raise UserRuleViolation("The last active admin cannot be demoted or deactivated")
    if user.id == actor.id and (demoting or deactivating or body.role not in (None, user.role)):
        raise UserRuleViolation("You cannot deactivate or change the role of your own account")
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    session.add(user)
    session.flush()
    if (demoting or deactivating) and not _active_admins(session):
        # Re-checked after our write holds the SQLite lock, in case another admin was removed meanwhile.
        session.rollback()
        raise UserRuleViolation("The last active admin cannot be demoted or deactivated")
    record_audit(
        session, actor, "user_update", "user", str(user.id), before=before, after=_view(user)
    )
    session.commit()
    return UserRow.model_validate(user, from_attributes=True)


def reset_password(session: Session, actor: User, user_id: int, body: PasswordReset) -> None:
    user = _get(session, user_id)
    user.password_hash = hash_password(body.password)
    session.add(user)
    record_audit(
        session,
        actor,
        "user_password_reset",
        "user",
        str(user.id),
        after={"username": user.username},
    )
    session.commit()

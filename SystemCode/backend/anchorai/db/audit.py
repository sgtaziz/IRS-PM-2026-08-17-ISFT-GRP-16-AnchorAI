from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlmodel import Session, func, select

from anchorai.db.models import AuditLog, User


def record_audit(
    session: Session,
    user: User | None,
    action: str,
    entity: str,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    """Stage an audit entry in the caller's transaction: mutate, record_audit, then commit."""
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action,
        entity=entity,
        entity_id=entity_id,
        before=before,
        after=after,
    )
    session.add(entry)
    return entry


class AuditRow(BaseModel):
    id: int
    ts: datetime
    username: str
    action: str
    entity: str
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class AuditPage(BaseModel):
    items: list[AuditRow]
    total: int
    actions: list[str]
    usernames: list[str]


def list_audit(
    session: Session,
    action: str | None = None,
    username: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditPage:
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if username:
        query = query.where(AuditLog.username == username)
    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    rows = session.exec(query.order_by(AuditLog.ts.desc()).offset(offset).limit(limit)).all()
    return AuditPage(
        items=[AuditRow.model_validate(r, from_attributes=True) for r in rows],
        total=total,
        actions=sorted(session.exec(select(AuditLog.action).distinct()).all()),
        usernames=sorted(session.exec(select(AuditLog.username).distinct()).all()),
    )

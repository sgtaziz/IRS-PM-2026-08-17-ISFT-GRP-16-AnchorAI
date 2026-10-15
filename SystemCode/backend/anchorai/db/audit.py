from typing import Any

from sqlmodel import Session

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

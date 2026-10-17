from typing import Annotated

from fastapi import APIRouter, Query

from anchorai.api.deps import SessionDep
from anchorai.db.audit import AuditPage, list_audit

router = APIRouter()


@router.get("", response_model=AuditPage)
def audit_log(
    session: SessionDep,
    action: str | None = None,
    username: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=2**63 - 1)] = 0,
):
    return list_audit(session, action, username, limit, offset)

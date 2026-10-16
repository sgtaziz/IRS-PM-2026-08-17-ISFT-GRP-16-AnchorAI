from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from anchorai.api.deps import SessionDep, require_role
from anchorai.db.audit import record_audit
from anchorai.db.models import User
from anchorai.discovery.service import DataNotBuilt
from anchorai.knowledge import reload
from anchorai.knowledge.reload import KgStatus

router = APIRouter()
Manager = Annotated[User, Depends(require_role("manager", "admin"))]


@router.get("/status", response_model=KgStatus)
def status(_: Manager):
    return reload.status()


@router.post("/reload", response_model=KgStatus)
def reload_graph(session: SessionDep, user: Manager):
    try:
        result = reload.sync_graph()
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    if result.stale:
        raise HTTPException(
            503, f"{result.error}. Saved edits will apply once the knowledge graph is reloaded."
        )
    record_audit(session, user, "kg.reload", "knowledge_graph", None, None, result.counts)
    session.commit()
    return result

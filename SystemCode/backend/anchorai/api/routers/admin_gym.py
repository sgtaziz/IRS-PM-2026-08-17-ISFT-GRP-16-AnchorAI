from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from anchorai.api.deps import SessionDep, require_role
from anchorai.assistant.classifier import refresh_names
from anchorai.db.models import User
from anchorai.discovery.service import DataNotBuilt
from anchorai.knowledge import reload, roster
from anchorai.knowledge.reload import KgStatus
from anchorai.knowledge.roster import ClassIn, EventIn, InstructorIn, ReassignIn, Roster

router = APIRouter()
Manager = Annotated[User, Depends(require_role("manager", "admin"))]


class Edit(BaseModel):
    """`kg.stale` means the edit is saved but the graph could not be rebuilt from it yet."""

    id: str | None = None
    kg: KgStatus


def _applied(session: Session, edit_id: str | None = None) -> Edit:
    refresh_names(session=session)
    return Edit(id=edit_id, kg=reload.sync_graph(session))


def _guarded(call, *args):
    try:
        return call(*args)
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    except roster.UnknownEntity as e:
        raise HTTPException(404, str(e)) from None
    except roster.Conflict as e:
        raise HTTPException(409, str(e)) from None


@router.get("", response_model=Roster)
def view(session: SessionDep, _: Manager):
    return _guarded(roster.roster, session)


@router.post("/instructors", response_model=Edit, status_code=201)
def add_instructor(body: InstructorIn, session: SessionDep, user: Manager):
    return _applied(session, _guarded(roster.add_instructor, session, user, body))


@router.post("/classes", response_model=Edit, status_code=201)
def add_class(body: ClassIn, session: SessionDep, user: Manager):
    return _applied(session, _guarded(roster.add_class, session, user, body))


@router.put("/classes/{class_id}/instructor", response_model=Edit)
def reassign_class(class_id: str, body: ReassignIn, session: SessionDep, user: Manager):
    _guarded(roster.reassign_class, session, user, class_id, body)
    return _applied(session, class_id)


@router.post("/events", response_model=Edit, status_code=201)
def record_event(body: EventIn, session: SessionDep, user: Manager):
    return _applied(session, _guarded(roster.record_event, session, user, body))


@router.delete("/events/{event_id}", response_model=Edit)
def revoke_event(event_id: str, session: SessionDep, user: Manager):
    _guarded(roster.revoke_event, session, user, event_id)
    return _applied(session, event_id)

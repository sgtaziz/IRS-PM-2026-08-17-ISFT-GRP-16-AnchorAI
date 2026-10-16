"""Admin edits to instructors, classes and events, and the roster view of the result.

Revoking a generated event writes a suppressing `GymEvent`, so it survives a data rebuild;
revoking an added one just deactivates it. Recording an event for an entity whose generated
event was revoked adds a new event (with its own week and note) alongside the suppression.
"""

import threading
from datetime import date
from functools import wraps
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints
from sqlmodel import Session

from anchorai.db.audit import record_audit
from anchorai.db.models import ClassInstructorOverride, GymClass, GymEvent, GymInstructor, User
from anchorai.discovery import service as member_data
from anchorai.knowledge import entities as ent
from anchorai.knowledge.entities import EventType


class RosterError(ValueError):
    pass


class UnknownEntity(RosterError):
    pass


class Conflict(RosterError):
    pass


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
_write_lock = threading.Lock()


def _serialised(fn):
    """One edit at a time, so ids, duplicate checks and event checks can't race."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        with _write_lock:
            return fn(*args, **kwargs)

    return wrapper


class InstructorIn(BaseModel):
    name: Name
    club_id: str


class ClassIn(BaseModel):
    name: Name
    club_id: str
    instructor_id: str


class ReassignIn(BaseModel):
    instructor_id: str


class EventIn(BaseModel):
    event_type: EventType
    entity_id: str
    week_start: date | None = None
    note: str = Field(default="", max_length=200)


class RosterEvent(BaseModel):
    event_id: str
    week_start: date
    note: str
    source: str


class RosterInstructor(BaseModel):
    id: str
    name: str
    club_id: str
    source: str
    status: str
    classes: int
    event: RosterEvent | None


class RosterClass(BaseModel):
    id: str
    name: str
    club_id: str
    instructor_id: str
    instructor_name: str
    source: str
    status: str
    event: RosterEvent | None


class Roster(BaseModel):
    clubs: list[str]
    instructors: list[RosterInstructor]
    classes: list[RosterClass]


def _day(value) -> date:
    return value.date() if hasattr(value, "date") else value


def _events_by_entity(eff: ent.Effective) -> dict[str, RosterEvent]:
    return {
        r.entity_id: RosterEvent(
            event_id=r.event_id,
            week_start=_day(r.week_start),
            note=r.note,
            source=r.source,
        )
        for r in eff.events.itertuples()
    }


def roster(session: Session) -> Roster:
    eff = ent.effective(session)
    events = _events_by_entity(eff)
    names = eff.instructors.set_index("instructor_id")["name"]
    taught = eff.classes["instructor_id"].value_counts()
    return Roster(
        clubs=sorted(member_data.get_data().tables["members"]["club_id"].unique()),
        instructors=[
            RosterInstructor(
                id=r.instructor_id,
                name=r.name,
                club_id=r.club_id,
                source=r.source,
                status="left" if r.instructor_id in events else "active",
                classes=int(taught.get(r.instructor_id, 0)),
                event=events.get(r.instructor_id),
            )
            for r in eff.instructors.itertuples()
        ],
        classes=[
            RosterClass(
                id=r.class_id,
                name=r.name,
                club_id=r.club_id,
                instructor_id=r.instructor_id,
                instructor_name=names.get(r.instructor_id, r.instructor_id),
                source=r.source,
                status="cancelled" if r.class_id in events else "active",
                event=events.get(r.class_id),
            )
            for r in eff.classes.itertuples()
        ],
    )


def _instructor_row(eff: ent.Effective, instructor_id: str):
    match = eff.instructors[eff.instructors["instructor_id"] == instructor_id]
    if match.empty:
        raise UnknownEntity(f"Unknown instructor {instructor_id}")
    return match.iloc[0]


def _require_present(eff: ent.Effective, instructor) -> None:
    if instructor["instructor_id"] in set(eff.events["entity_id"]):
        raise Conflict(f"{instructor['name']} has left; reinstate them first")


def _require_new_name(frame, name: str, noun: str) -> None:
    if name.casefold() in set(frame["name"].str.casefold()):
        raise Conflict(f"A {noun} named {name} already exists")


def _check_club(club_id: str) -> None:
    if club_id not in set(member_data.get_data().tables["members"]["club_id"]):
        raise UnknownEntity(f"Unknown club {club_id}")


@_serialised
def add_instructor(session: Session, actor: User, body: InstructorIn) -> str:
    _check_club(body.club_id)
    eff = ent.effective(session)
    _require_new_name(eff.instructors, body.name, "instructor")
    row = GymInstructor(
        instructor_id=ent.next_id(ent.INSTRUCTOR_PREFIX, list(eff.instructors["instructor_id"])),
        name=body.name.strip(),
        club_id=body.club_id,
        created_by_id=actor.id,
    )
    session.add(row)
    record_audit(
        session, actor, "gym.instructor_add", "instructor", row.instructor_id, None,
        {"name": row.name, "club_id": row.club_id},
    )  # fmt: skip
    session.commit()
    return row.instructor_id


@_serialised
def add_class(session: Session, actor: User, body: ClassIn) -> str:
    _check_club(body.club_id)
    eff = ent.effective(session)
    _require_new_name(eff.classes, body.name, "class")
    instructor = _instructor_row(eff, body.instructor_id)
    if instructor["club_id"] != body.club_id:
        raise Conflict(f"{instructor['name']} works at {instructor['club_id']}, not {body.club_id}")
    _require_present(eff, instructor)
    row = GymClass(
        class_id=ent.next_id(ent.CLASS_PREFIX, list(eff.classes["class_id"])),
        name=body.name.strip(),
        club_id=body.club_id,
        instructor_id=body.instructor_id,
        created_by_id=actor.id,
    )
    session.add(row)
    record_audit(
        session, actor, "gym.class_add", "class", row.class_id, None,
        {"name": row.name, "club_id": row.club_id, "instructor_id": row.instructor_id},
    )  # fmt: skip
    session.commit()
    return row.class_id


@_serialised
def reassign_class(session: Session, actor: User, class_id: str, body: ReassignIn) -> None:
    eff = ent.effective(session)
    match = eff.classes[eff.classes["class_id"] == class_id]
    if match.empty:
        raise UnknownEntity(f"Unknown class {class_id}")
    current = match.iloc[0]
    instructor = _instructor_row(eff, body.instructor_id)
    if instructor["club_id"] != current["club_id"]:
        raise Conflict(
            f"{instructor['name']} works at {instructor['club_id']}, "
            f"but the class is at {current['club_id']}"
        )
    _require_present(eff, instructor)
    if current["instructor_id"] == body.instructor_id:
        raise Conflict(f"{instructor['name']} already teaches this class")
    override = session.get(ClassInstructorOverride, class_id)
    if override is None:
        override = ClassInstructorOverride(class_id=class_id, instructor_id=body.instructor_id)
    override.instructor_id = body.instructor_id
    override.updated_by_id = actor.id
    session.add(override)
    record_audit(
        session, actor, "gym.class_reassign", "class", class_id,
        {"instructor_id": current["instructor_id"]}, {"instructor_id": body.instructor_id},
    )  # fmt: skip
    session.commit()


@_serialised
def record_event(session: Session, actor: User, body: EventIn, today: date | None = None) -> str:
    eff = ent.effective(session)
    frame, column, noun = (
        (eff.instructors, "instructor_id", "instructor")
        if body.event_type == "instructor_left"
        else (eff.classes, "class_id", "class")
    )
    if body.entity_id not in set(frame[column]):
        raise UnknownEntity(f"Unknown {noun} {body.entity_id}")
    if body.entity_id in set(eff.events["entity_id"]):
        raise Conflict(f"{body.entity_id} already has an active event; revoke it first")
    row = GymEvent(
        event_type=body.event_type,
        entity_id=body.entity_id,
        week_start=body.week_start or ent.current_week(today),
        note=body.note.strip(),
        created_by_id=actor.id,
    )
    session.add(row)
    session.flush()
    record_audit(
        session, actor, "gym.event_record", "event", ent.event_id(row), None,
        {
            "event_type": row.event_type,
            "entity_id": row.entity_id,
            "week_start": row.week_start.isoformat(),
            "note": row.note,
        },
    )  # fmt: skip
    session.commit()
    return ent.event_id(row)


@_serialised
def revoke_event(session: Session, actor: User, event_id: str) -> None:
    eff = ent.effective(session)
    match = eff.events[eff.events["event_id"] == event_id]
    if match.empty:
        raise UnknownEntity(f"No active event {event_id}")
    event = match.iloc[0]
    before = {
        "event_type": event["event_type"],
        "entity_id": event["entity_id"],
        "week_start": _day(event["week_start"]).isoformat(),
    }
    if event["source"] == ent.ADDED:
        eff.overlay_events[event_id].active = False
        session.add(eff.overlay_events[event_id])
    else:
        session.add(
            GymEvent(
                event_type=event["event_type"],
                entity_id=event["entity_id"],
                week_start=_day(event["week_start"]),
                suppresses=event_id,
                created_by_id=actor.id,
            )
        )
    record_audit(session, actor, "gym.event_revoke", "event", event_id, before, None)
    session.commit()

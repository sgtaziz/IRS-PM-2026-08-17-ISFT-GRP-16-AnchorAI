"""Instructors, classes and events as the app sees them: Stream A's tables plus admin edits.

A data rebuild overwrites the generated tables, so edits live in SQLite and are merged on read:
added instructors and classes get `IX`/`KX` ids that cannot clash with generated `I`/`K` ids; an
override says who teaches a class now; an event row adds an event, or (with `suppresses`) hides a
generated one. The overlay never changes attendance, so an added class has no members until the
data is rebuilt.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

import pandas as pd
from sqlmodel import Session, select

from anchorai.db.models import ClassInstructorOverride, GymClass, GymEvent, GymInstructor
from anchorai.db.session import get_engine
from anchorai.discovery import service as member_data

INSTRUCTOR_PREFIX = "IX"
CLASS_PREFIX = "KX"
EVENT_PREFIX = "EX"
GENERATED, ADDED = "generated", "added"
EventType = Literal["instructor_left", "class_cancelled"]


@dataclass
class Effective:
    instructors: pd.DataFrame
    classes: pd.DataFrame
    events: pd.DataFrame
    overlay_events: dict[str, GymEvent]


def current_week(today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def next_id(prefix: str, existing: list[str]) -> str:
    numbers = [int(i.removeprefix(prefix)) for i in existing if i.startswith(prefix)]
    return f"{prefix}{max(numbers, default=0) + 1:02d}"


def event_id(event: GymEvent) -> str:
    return f"{EVENT_PREFIX}{event.id:03d}"


def merge(
    tables: dict[str, pd.DataFrame],
    instructors: list[GymInstructor],
    classes: list[GymClass],
    overrides: list[ClassInstructorOverride],
    events: list[GymEvent],
) -> Effective:
    """The generated tables with the overlay applied; each frame gets a `source` column."""
    base_instructors = tables["instructors"].assign(source=GENERATED)
    added_instructors = pd.DataFrame(
        [(i.instructor_id, i.name, i.club_id, ADDED) for i in instructors],
        columns=["instructor_id", "name", "club_id", "source"],
    )
    all_instructors = pd.concat([base_instructors, added_instructors], ignore_index=True)

    base_classes = tables["classes"].assign(source=GENERATED)
    added_classes = pd.DataFrame(
        [(c.class_id, c.name, c.club_id, c.instructor_id, ADDED) for c in classes],
        columns=["class_id", "name", "club_id", "instructor_id", "source"],
    )
    all_classes = pd.concat([base_classes, added_classes], ignore_index=True)
    taught_by = {o.class_id: o.instructor_id for o in overrides}
    all_classes["instructor_id"] = (
        all_classes["class_id"].map(taught_by).fillna(all_classes["instructor_id"])
    )

    scenario = tables["events"]
    hidden = {e.suppresses for e in events if e.active and e.suppresses}
    kept = scenario[~scenario["event_id"].isin(hidden)].assign(note="", source=GENERATED)
    added = {event_id(e): e for e in events if e.active and not e.suppresses}
    added_frame = pd.DataFrame(
        [
            (k, e.event_type, e.entity_id, pd.Timestamp(e.week_start), e.note, ADDED)
            for k, e in added.items()
        ],
        columns=["event_id", "event_type", "entity_id", "week_start", "note", "source"],
    )
    all_events = pd.concat([kept, added_frame], ignore_index=True)
    return Effective(all_instructors, all_classes, all_events, added)


def load_overlay(session: Session) -> tuple[list, list, list, list]:
    return (
        list(session.exec(select(GymInstructor).order_by(GymInstructor.instructor_id))),
        list(session.exec(select(GymClass).order_by(GymClass.class_id))),
        list(session.exec(select(ClassInstructorOverride))),
        list(session.exec(select(GymEvent).order_by(GymEvent.id))),
    )


def effective(session: Session | None = None) -> Effective:
    tables = member_data.get_data().tables
    if session is not None:
        return merge(tables, *load_overlay(session))
    with Session(get_engine()) as own:
        return merge(tables, *load_overlay(own))


def effective_tables(session: Session | None = None) -> dict[str, pd.DataFrame]:
    """The data tables with the effective instructors, classes and events swapped in."""
    eff = effective(session)
    return {
        **member_data.get_data().tables,
        "instructors": eff.instructors,
        "classes": eff.classes,
        "events": eff.events,
    }

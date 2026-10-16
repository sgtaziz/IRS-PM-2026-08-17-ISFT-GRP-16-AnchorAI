"""What-if events for the graph explorer: who an instructor leaving or a class closing would hit.

Read-only: the graph and the data tables are not changed; the KG facts are overridden in memory.
"""

from pydantic import BaseModel
from sqlmodel import Session

from anchorai.discovery import service as member_data
from anchorai.knowledge import entities as effective_entities
from anchorai.knowledge import queries
from anchorai.knowledge.entities import EventType
from anchorai.knowledge.graph import read
from anchorai.knowledge.signals import ANCHOR_SHARE_THRESHOLD
from anchorai.reasoning import service as reasoning
from anchorai.reasoning.engine import run
from anchorai.reasoning.models import Proposal


class Entity(BaseModel):
    id: str
    name: str
    club_id: str
    detail: str
    has_event: bool


class Entities(BaseModel):
    instructors: list[Entity]
    classes: list[Entity]


class AffectedMember(BaseModel):
    member_id: str
    churn_prob: float
    risk_band: str
    share: float | None
    new_rules: list[str]
    allowed: list[Proposal]


class Simulation(BaseModel):
    event_type: EventType
    entity_id: str
    label: str
    affected: int
    high_risk: int
    newly_flagged: int
    members: list[AffectedMember]


def entities(session: Session | None = None) -> Entities:
    eff = effective_entities.effective(session)
    events = set(eff.events["entity_id"])
    instructors = eff.instructors
    classes = eff.classes.merge(
        instructors[["instructor_id", "name"]], on="instructor_id", suffixes=("", "_instructor")
    )
    return Entities(
        instructors=[
            Entity(
                id=r.instructor_id,
                name=r.name,
                club_id=r.club_id,
                detail="",
                has_event=r.instructor_id in events,
            )
            for r in instructors.itertuples()
        ],
        classes=[
            Entity(
                id=r.class_id,
                name=r.name,
                club_id=r.club_id,
                detail=f"with {r.name_instructor}",
                has_event=r.class_id in events,
            )
            for r in classes.itertuples()
        ],
    )


def simulate(session: Session, event_type: EventType, entity_id: str) -> Simulation | None:
    data = member_data.get_data()
    eff = effective_entities.effective(session)
    if event_type == "instructor_left":
        names = eff.instructors.set_index("instructor_id")["name"]
        if entity_id not in names:
            return None
        label = f"{names[entity_id]} leaves"
        hits = {
            r["member_id"]: r["share"]
            for r in read(queries.SHARE_WITH_INSTRUCTOR, instructor_id=entity_id)
        }
    else:
        names = eff.classes.set_index("class_id")["name"]
        if entity_id not in names:
            return None
        label = f"the {names[entity_id]} class is cancelled"
        hits = {r["member_id"]: None for r in read(queries.MEMBERS_BY_CLASS, class_id=entity_id)}

    already_happened = entity_id in set(eff.events["entity_id"])
    _, rules = reasoning.active_rules(session)
    all_facts = reasoning.all_facts()
    members = []
    for member_id, share in hits.items():
        if member_id not in all_facts:
            continue
        before = run(rules, all_facts[member_id], member_id)
        facts = dict(all_facts[member_id])
        if event_type == "instructor_left":
            # The stored share sums every instructor who has already left; add this one
            # unless they're among them.
            existing = facts.get("anchor_instructor_share") or 0.0
            combined = existing if already_happened else min(1.0, existing + share)
            facts["anchor_instructor_share"] = combined
            facts["lost_anchor_instructor"] = combined >= ANCHOR_SHARE_THRESHOLD
        else:
            facts["class_cancelled"] = True
        after = run(rules, facts, member_id)
        fired_before = {f.rule_id for f in before.firings}
        row = data.table.loc[member_id]
        members.append(
            AffectedMember(
                member_id=member_id,
                churn_prob=float(row["churn_prob"]),
                risk_band=str(row["risk_band"]),
                share=None if share is None else round(float(share), 3),
                new_rules=[f.rule_id for f in after.firings if f.rule_id not in fired_before],
                allowed=after.allowed,
            )
        )
    members.sort(key=lambda m: -m.churn_prob)
    return Simulation(
        event_type=event_type,
        entity_id=entity_id,
        label=label,
        affected=len(members),
        high_risk=sum(m.risk_band == "high" for m in members),
        newly_flagged=sum(bool(m.new_rules) for m in members),
        members=members,
    )

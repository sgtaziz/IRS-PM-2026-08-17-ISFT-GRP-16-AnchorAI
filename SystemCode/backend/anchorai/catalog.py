"""Offers, staff roster and planning constraints (W41): the inputs the weekly plan reads."""

import random
from typing import Any

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from anchorai.db.audit import record_audit
from anchorai.db.models import AppSetting, OfferCatalog, StaffProfile, User, utcnow
from anchorai.scenario.offers import OFFER_CATALOG
from anchorai.schemas import Channel

DEFAULT_CONSTRAINTS: dict[str, Any] = {
    "default_budget": 1500.0,
    "default_staff_minutes": 2160,
    "max_contacts_per_member_per_30d": 1,
    "max_offers_per_member_per_90d": 2,
}
DEFAULT_ROSTER = {
    "staff1": (20.0, ["trainer", "calls"]),
    "staff2": (16.0, ["calls"]),
}
SKILLS = ["trainer", "calls", "front_desk"]


class OfferIn(BaseModel):
    offer_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1)
    cost: float = Field(ge=0)
    staff_minutes: int = Field(ge=0)
    inventory: int | None = Field(default=None, ge=0)
    channels: list[Channel] = Field(min_length=1)
    eligibility: str = ""
    required_skill: str = ""
    active: bool = True


class StaffIn(BaseModel):
    weekly_hours: float = Field(ge=0, le=60)
    skills: list[str] = []


class StaffRow(StaffIn):
    user_id: int
    username: str
    full_name: str


class Constraints(BaseModel):
    default_budget: float = Field(ge=0)
    default_staff_minutes: int = Field(ge=0)
    max_contacts_per_member_per_30d: int = Field(ge=0)
    max_offers_per_member_per_90d: int = Field(ge=0)


class CatalogView(BaseModel):
    offers: list[OfferIn]
    staff: list[StaffRow]
    constraints: Constraints
    skills: list[str]


def _offer_dict(row: OfferCatalog) -> dict:
    return OfferIn.model_validate(row, from_attributes=True).model_dump(mode="json")


def list_offers(session: Session, active_only: bool = False) -> list[OfferIn]:
    query = select(OfferCatalog).order_by(OfferCatalog.offer_id)
    if active_only:
        query = query.where(OfferCatalog.active)
    return [OfferIn.model_validate(r, from_attributes=True) for r in session.exec(query)]


def list_staff(session: Session) -> list[StaffRow]:
    users = session.exec(
        select(User).where(User.role == "staff", User.is_active).order_by(User.username)
    )
    rows = []
    for user in users:
        profile = session.get(StaffProfile, user.id) or StaffProfile(user_id=user.id)
        rows.append(
            StaffRow(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                weekly_hours=profile.weekly_hours,
                skills=profile.skills,
            )
        )
    return rows


def get_constraints(session: Session) -> Constraints:
    stored = {s.key: s.value for s in session.exec(select(AppSetting))}
    return Constraints(**{**DEFAULT_CONSTRAINTS, **stored})


def view(session: Session) -> CatalogView:
    return CatalogView(
        offers=list_offers(session),
        staff=list_staff(session),
        constraints=get_constraints(session),
        skills=SKILLS,
    )


def upsert_offer(session: Session, user: User, offer: OfferIn) -> OfferIn:
    row = session.get(OfferCatalog, offer.offer_id)
    before = _offer_dict(row) if row else None
    data = offer.model_dump(mode="json")
    if row is None:
        row = OfferCatalog(**data)
    else:
        for key, value in data.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
    session.add(row)
    action = "offer.update" if before else "offer.create"
    record_audit(session, user, action, "offer", offer.offer_id, before, data)
    session.commit()
    return offer


def delete_offer(session: Session, user: User, offer_id: str) -> bool:
    row = session.get(OfferCatalog, offer_id)
    if row is None:
        return False
    record_audit(session, user, "offer.delete", "offer", offer_id, _offer_dict(row), None)
    session.delete(row)
    session.commit()
    return True


def update_staff(session: Session, user: User, staff_id: int, change: StaffIn) -> StaffRow | None:
    member = session.get(User, staff_id)
    if member is None or member.role != "staff" or not member.is_active:
        return None
    profile = session.get(StaffProfile, staff_id) or StaffProfile(user_id=staff_id)
    before = {"weekly_hours": profile.weekly_hours, "skills": profile.skills}
    profile.weekly_hours, profile.skills = change.weekly_hours, list(change.skills)
    session.add(profile)
    record_audit(session, user, "staff.update", "staff", str(staff_id), before, change.model_dump())
    session.commit()
    return next(r for r in list_staff(session) if r.user_id == staff_id)


def update_constraints(session: Session, user: User, change: Constraints) -> Constraints:
    before = get_constraints(session).model_dump()
    for key, value in change.model_dump().items():
        row = session.get(AppSetting, key) or AppSetting(key=key, value=value)
        row.value, row.updated_at = value, utcnow()
        session.add(row)
    record_audit(
        session, user, "constraints.update", "constraints", None, before, change.model_dump()
    )
    session.commit()
    return change


def seed(session: Session, rng: random.Random) -> None:
    """Offer catalogue, staff roster and default constraints; inserts only what is missing.

    Offers are seeded only into an empty catalogue: the API container seeds on every start, and
    re-inserting a seeded offer would undo an admin's (audited) deletion.
    """
    if session.exec(select(OfferCatalog.offer_id)).first() is None:
        for offer in OFFER_CATALOG:
            session.add(OfferCatalog(**offer))
    for username, (hours, skills) in DEFAULT_ROSTER.items():
        user = session.exec(select(User).where(User.username == username)).first()
        if user is not None and session.get(StaffProfile, user.id) is None:
            session.add(StaffProfile(user_id=user.id, weekly_hours=hours, skills=skills))
    for key, value in DEFAULT_CONSTRAINTS.items():
        if session.get(AppSetting, key) is None:
            session.add(AppSetting(key=key, value=value))

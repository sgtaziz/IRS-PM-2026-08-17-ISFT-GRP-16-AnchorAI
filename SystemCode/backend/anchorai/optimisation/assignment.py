"""Assign an approved plan's contacts to staff by weekly hours and skills (W16), and print call sheets."""

import csv
import io

from sqlmodel import Session, col, delete, select

from anchorai import catalog
from anchorai.catalog import OfferIn, StaffRow
from anchorai.db import models
from anchorai.db.audit import record_audit
from anchorai.optimisation.overrides import PlanNotFound
from anchorai.schemas import Channel


class NotApproved(RuntimeError):
    pass


class CannotAssign(ValueError):
    pass


def required_skill(offer: OfferIn, channel: str) -> str | None:
    """The skill a contact needs: the offer's own (PT needs a trainer), else `calls` for a phone call."""
    if offer.required_skill:
        return offer.required_skill
    return "calls" if channel == Channel.CALL else None


def _approved(session: Session, plan_id: int) -> models.Plan:
    plan = session.get(models.Plan, plan_id)
    if plan is None:
        raise PlanNotFound(plan_id)
    if plan.status != "approved":
        raise NotApproved(f"Plan {plan_id} must be approved before it is assigned")
    return plan


def _items(session: Session, plan_id: int) -> list[models.PlanItem]:
    return list(
        session.exec(
            select(models.PlanItem)
            .where(models.PlanItem.plan_id == plan_id, col(models.PlanItem.removed).is_(False))
            .order_by(col(models.PlanItem.expected_value).desc(), col(models.PlanItem.id))
        ).all()
    )


def _can_take(member: StaffRow, skill: str | None) -> bool:
    return skill is None or skill in member.skills


def assign(session: Session, user: models.User, plan_id: int) -> dict:
    """Replace the plan's assignments: most valuable first, each to the eligible staff member with the most
    free minutes. Returns the summary with any contacts nobody could take."""
    _approved(session, plan_id)
    offers = {o.offer_id: o for o in catalog.list_offers(session)}
    staff = catalog.list_staff(session)
    free = {s.user_id: 60 * s.weekly_hours for s in staff}
    items = _items(session, plan_id)
    session.exec(
        delete(models.Assignment).where(
            col(models.Assignment.plan_item_id).in_([i.id for i in items])
        )
    )
    counts: dict[int, int] = {}
    unassigned = []
    for item in items:
        offer = offers[item.offer_id]
        skill = required_skill(offer, item.channel)
        eligible = [
            s for s in staff if _can_take(s, skill) and free[s.user_id] >= offer.staff_minutes
        ]
        if not eligible:
            unassigned.append(item.member_id)
            continue
        chosen = max(eligible, key=lambda s: (free[s.user_id], -s.user_id))
        free[chosen.user_id] -= offer.staff_minutes
        counts[chosen.user_id] = counts.get(chosen.user_id, 0) + 1
        session.add(
            models.Assignment(
                plan_item_id=item.id, staff_user_id=chosen.user_id, priority=counts[chosen.user_id]
            )
        )
    after = {"assigned": sum(counts.values()), "unassigned": len(unassigned)}
    record_audit(session, user, "plan.assign", "plan", str(plan_id), None, after)
    session.commit()
    return summary(session, plan_id)


def reassign(
    session: Session, user: models.User, plan_id: int, member_id: str, staff_user_id: int
) -> dict:
    """Move one contact to another staff member, if they have the skill and the minutes."""
    _approved(session, plan_id)
    item = next((i for i in _items(session, plan_id) if i.member_id == member_id), None)
    if item is None:
        raise CannotAssign(f"{member_id} is not in plan {plan_id}")
    staff = {s.user_id: s for s in catalog.list_staff(session)}
    target = staff.get(staff_user_id)
    if target is None:
        raise CannotAssign(f"No active staff member {staff_user_id}")
    offers = {o.offer_id: o for o in catalog.list_offers(session)}
    offer = offers[item.offer_id]
    skill = required_skill(offer, item.channel)
    if not _can_take(target, skill):
        raise CannotAssign(f"{target.full_name} lacks the {skill} skill this contact needs")
    current = session.exec(
        select(models.Assignment).where(models.Assignment.plan_item_id == item.id)
    ).first()
    load = next(s for s in summary(session, plan_id)["staff"] if s["user_id"] == staff_user_id)
    if load["minutes_used"] + offer.staff_minutes > 60 * target.weekly_hours:
        raise CannotAssign(f"{target.full_name} has no time left this week for this contact")
    before = {"staff_user_id": current.staff_user_id} if current else None
    if current is None:
        current = models.Assignment(plan_item_id=item.id, staff_user_id=staff_user_id)
    current.staff_user_id = staff_user_id
    current.priority = len(load["contacts"]) + 1  # last in the new staff member's list
    session.add(current)
    after = {"member_id": member_id, "staff_user_id": staff_user_id}
    record_audit(session, user, "plan.reassign", "plan", str(plan_id), before, after)
    session.commit()
    return summary(session, plan_id)


def summary(session: Session, plan_id: int) -> dict:
    """Per staff member: minutes used against capacity and their contacts in priority order."""
    offers = {o.offer_id: o for o in catalog.list_offers(session)}
    items = {i.id: i for i in _items(session, plan_id)}
    rows = session.exec(
        select(models.Assignment)
        .where(col(models.Assignment.plan_item_id).in_(list(items)))
        .order_by(col(models.Assignment.priority))
    ).all()
    by_staff: dict[int, list] = {}
    for a in rows:
        by_staff.setdefault(a.staff_user_id, []).append(items[a.plan_item_id])
    assigned = {a.plan_item_id for a in rows}
    staff = []
    for s in catalog.list_staff(session):
        mine = by_staff.get(s.user_id, [])
        staff.append(
            {
                "user_id": s.user_id,
                "full_name": s.full_name,
                "skills": s.skills,
                "minutes_capacity": int(60 * s.weekly_hours),
                "minutes_used": sum(offers[i.offer_id].staff_minutes for i in mine),
                "contacts": [
                    {"member_id": i.member_id, "offer_id": i.offer_id, "channel": i.channel}
                    for i in mine
                ],
            }
        )
    unassigned = [i.member_id for i in items.values() if i.id not in assigned]
    return {"plan_id": plan_id, "staff": staff, "unassigned": unassigned}


def call_sheet(session: Session, plan_id: int, staff_user_id: int) -> str:
    """CSV call sheet for one staff member: priority, member, offer, channel and the talking point."""
    offers = {o.offer_id: o.name for o in catalog.list_offers(session)}
    rows = session.exec(
        select(models.Assignment, models.PlanItem)
        .join(models.PlanItem, col(models.PlanItem.id) == col(models.Assignment.plan_item_id))
        .where(
            models.PlanItem.plan_id == plan_id,
            col(models.PlanItem.removed).is_(False),
            models.Assignment.staff_user_id == staff_user_id,
        )
        .order_by(col(models.Assignment.priority))
    ).all()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["priority", "member_id", "offer", "channel", "talking_point"])
    for a, item in rows:
        point = (item.explanation or {}).get("summary", "")
        writer.writerow(
            [
                a.priority,
                item.member_id,
                offers.get(item.offer_id, item.offer_id),
                item.channel,
                point,
            ]
        )
    return out.getvalue()

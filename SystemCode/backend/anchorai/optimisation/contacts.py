"""Contact and outcome history from approved plans: what staff did and what happened."""

from sqlmodel import Session, col, select

from anchorai import catalog
from anchorai.db import models


def history(session: Session, member_id: str) -> list[dict]:
    """Every contact planned for the member in an approved plan, newest week first, with its outcomes."""
    names = {o.offer_id: o.name for o in catalog.list_offers(session)}
    rows = session.exec(
        select(models.PlanItem, models.Plan)
        .join(models.Plan, col(models.Plan.id) == col(models.PlanItem.plan_id))
        .where(models.PlanItem.member_id == member_id, models.Plan.status == "approved")
        .order_by(col(models.Plan.week_start).desc(), col(models.PlanItem.id))
    ).all()
    out = []
    for item, plan in rows:
        assigned = session.exec(
            select(models.Assignment, models.User)
            .join(models.User, col(models.User.id) == col(models.Assignment.staff_user_id))
            .where(models.Assignment.plan_item_id == item.id)
        ).first()
        outcomes = session.exec(
            select(models.Outcome)
            .where(models.Outcome.plan_item_id == item.id)
            .order_by(col(models.Outcome.logged_at))
        ).all()
        out.append(
            {
                "plan_id": plan.id,
                "week_start": plan.week_start.isoformat(),
                "offer_id": item.offer_id,
                "offer_name": names.get(item.offer_id, item.offer_id),
                "channel": item.channel,
                "removed": item.removed,
                "override_reason": item.override_reason,
                "assigned_to": assigned[1].full_name if assigned else None,
                "outcomes": [
                    {"outcome": o.outcome, "note": o.note, "logged_at": o.logged_at.isoformat()}
                    for o in outcomes
                ],
            }
        )
    return out

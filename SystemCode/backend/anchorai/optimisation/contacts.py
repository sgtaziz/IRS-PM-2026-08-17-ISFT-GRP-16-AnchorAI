"""Contact and outcome history from approved plans: what staff did and what happened."""

import pandas as pd
from sqlmodel import Session, col, select

from anchorai import catalog
from anchorai.cbr.reasoner import CASE_COLUMNS, CaseBase, load_case_base, retain
from anchorai.db import models
from anchorai.db.audit import record_audit
from anchorai.features import LABELS


def history(session: Session, member_id: str) -> list[dict]:
    """Every contact planned for the member in an approved plan, newest week first, with its outcomes."""
    names = {o.offer_id: o.name for o in catalog.list_offers(session)}
    rows = session.exec(
        select(models.PlanItem, models.Plan)
        .join(models.Plan, col(models.Plan.id) == col(models.PlanItem.plan_id))
        .where(models.PlanItem.member_id == member_id, models.Plan.status == "approved")
        .order_by(
            col(models.Plan.week_start).desc(), col(models.Plan.id).desc(), col(models.PlanItem.id)
        )
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


OUTCOMES = ["reached", "no_answer", "accepted", "declined", "follow_up"]
# What a logged outcome says about staying, by Stream A's dashboard definition (RETAINED = accepted).
STAYED = {"accepted": True, "declined": False}


class NotYours(PermissionError):
    pass


class UnknownContact(LookupError):
    pass


def logged_cases(session: Session) -> pd.DataFrame:
    """Logged outcomes that say whether the member stayed, shaped as CBR cases (the retain step)."""
    rows = session.exec(
        select(models.Outcome, models.PlanItem, models.Plan)
        .join(models.PlanItem, col(models.PlanItem.id) == col(models.Outcome.plan_item_id))
        .join(models.Plan, col(models.Plan.id) == col(models.PlanItem.plan_id))
        .where(col(models.Outcome.outcome).in_(list(STAYED)))
    ).all()
    return pd.DataFrame(
        [
            {
                "member_id": item.member_id,
                "offer_id": item.offer_id,
                "week_start": pd.Timestamp(plan.week_start),
                "treated": True,
                "stayed": STAYED[outcome.outcome],
            }
            for outcome, item, plan in rows
        ],
        columns=CASE_COLUMNS,
    )


def app_case_base(session: Session) -> CaseBase:
    """The randomised intervention log plus the app's logged outcomes. Experiments use the log alone."""
    base = load_case_base()
    logged = logged_cases(session)
    return retain(base, logged) if len(logged) else base


def _latest_approved(session: Session) -> models.Plan | None:
    return session.exec(
        select(models.Plan)
        .where(models.Plan.status == "approved")
        .order_by(col(models.Plan.week_start).desc(), col(models.Plan.id).desc())
    ).first()


def my_contacts(session: Session, user: models.User) -> list[dict]:
    """The user's contacts in the latest approved plan, in priority order, with talking points."""
    plan = _latest_approved(session)
    if plan is None:
        return []
    names = {o.offer_id: o.name for o in catalog.list_offers(session)}
    rows = session.exec(
        select(models.Assignment, models.PlanItem)
        .join(models.PlanItem, col(models.PlanItem.id) == col(models.Assignment.plan_item_id))
        .where(
            models.PlanItem.plan_id == plan.id,
            col(models.PlanItem.removed).is_(False),
            models.Assignment.staff_user_id == user.id,
        )
        .order_by(col(models.Assignment.priority))
    ).all()
    out = []
    for a, item in rows:
        why = item.explanation or {}
        logged = session.exec(
            select(models.Outcome).where(models.Outcome.plan_item_id == item.id)
        ).first()
        rule = next(
            (
                f["description"]
                for f in why.get("rule_trace", [])
                if f["effect"].startswith("propose " + item.offer_id)
            ),
            None,
        )
        out.append(
            {
                "plan_id": plan.id,
                "week_start": plan.week_start.isoformat(),
                "plan_item_id": item.id,
                "priority": a.priority,
                "member_id": item.member_id,
                "offer_id": item.offer_id,
                "offer_name": names.get(item.offer_id, item.offer_id),
                "channel": item.channel,
                "explanation_id": item.explanation_id,
                "summary": why.get("summary", ""),
                "drivers": [LABELS.get(n, n) for n, v in why.get("top_drivers", []) if v > 0][:3],
                "rule": rule,
                "graph_signals": why.get("graph_signals", []),
                "outcome": logged.outcome if logged else None,
                "note": logged.note if logged else None,
            }
        )
    return out


def log_outcome(
    session: Session, user: models.User, plan_item_id: int, outcome: str, note: str | None
) -> dict:
    """Record what happened with one contact. One outcome per contact: logging again updates it."""
    item = session.get(models.PlanItem, plan_item_id)
    plan = session.get(models.Plan, item.plan_id) if item else None
    if item is None or item.removed or plan.status != "approved":
        raise UnknownContact(f"No contact {plan_item_id} in an approved plan")
    assigned = session.exec(
        select(models.Assignment).where(models.Assignment.plan_item_id == item.id)
    ).first()
    if user.role == "staff" and (assigned is None or assigned.staff_user_id != user.id):
        raise NotYours(f"Contact {plan_item_id} is assigned to someone else")
    row = session.exec(select(models.Outcome).where(models.Outcome.plan_item_id == item.id)).first()
    before = {"outcome": row.outcome, "note": row.note} if row else None
    if row is None:
        row = models.Outcome(
            plan_item_id=item.id, member_id=item.member_id, logged_by_id=user.id, outcome=outcome
        )
    row.outcome, row.note, row.logged_by_id, row.logged_at = outcome, note, user.id, models.utcnow()
    session.add(row)
    after = {"member_id": item.member_id, "outcome": outcome, "note": note}
    record_audit(session, user, "outcome.log", "plan_item", str(item.id), before, after)
    session.commit()
    return {"plan_item_id": item.id, "member_id": item.member_id, "outcome": outcome, "note": note}

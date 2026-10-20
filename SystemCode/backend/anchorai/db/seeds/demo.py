"""Demo layer (Stream B): one approved past week built by the planner, assigned, with logged outcomes.

Dashboards, the audit log, the assistant's plan answers and the CBR retain loop then have data on a fresh
clone. What members did that week is simulated with the scenario's own response model, as the intervention
history was; it describes outcomes and never chooses a contact.
"""

import random
from datetime import UTC, date, datetime, time, timedelta

import numpy as np
from sqlmodel import Session, col, select

from anchorai import catalog
from anchorai.db.models import Assignment, AuditLog, Outcome, Plan, PlanItem, User
from anchorai.discovery.service import DataNotBuilt
from anchorai.optimisation import assignment, contacts, overrides, service
from anchorai.scenario.tables import read_tables
from anchorai.schemas import PlanRequest

# The Monday after the scenario's last intervention week (2026-10-05), so the demo week is "last week".
DEMO_WEEK = date(2026, 10, 12)
NO_ANSWER = 0.2
FOLLOW_UP = 0.1  # share of reached members who ask to be called back instead of deciding


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(DEMO_WEEK + timedelta(days=day), time(hour, minute), tzinfo=UTC)


WORKDAY_MINUTES = 7 * 60  # calls are made 10:00 to 17:00, Monday to Friday


def _spread(k: int, n: int) -> datetime:
    """The k-th of n outcomes, evenly spread over the working week."""
    offset = k * 5 * WORKDAY_MINUTES // max(n, 1)
    day, minutes = divmod(offset, WORKDAY_MINUTES)
    return _at(day, 10) + timedelta(minutes=minutes)


def seed(session: Session, rng: random.Random) -> None:
    if session.exec(select(Plan).where(Plan.week_start == DEMO_WEEK)).first() is not None:
        return
    manager = session.exec(select(User).where(User.username == "manager")).first()
    if manager is None:
        return
    limits = catalog.get_constraints(session)
    request = PlanRequest(
        as_of=DEMO_WEEK,
        budget=limits.default_budget,
        staff_minutes=limits.default_staff_minutes,
        # At the seeded 36 h the GA finds the greedy plan (E4), and greedy keeps `db reset` fast.
        solver="greedy",
    )
    try:
        saved = service.build_plan(session, manager, request)
        tables = read_tables()
    except (DataNotBuilt, FileNotFoundError):
        return  # base-only clone: the data tables are built later by `anchorai data build`
    overrides.approve(session, manager, saved.id)
    assignment.assign(session, manager, saved.id)
    _log_outcomes(session, saved.id, tables, rng)
    _backdate(session, saved.id)


def _log_outcomes(session: Session, plan_id: int, tables: dict, rng: random.Random) -> None:
    truth = tables["true_uplift"].set_index(["member_id", "offer_id"])["uplift"]
    churn = tables["true_churn"].set_index("member_id")["event_churn"]
    staff = {u.id: u for u in session.exec(select(User)).all()}
    rows = session.exec(
        select(PlanItem.id, PlanItem.member_id, PlanItem.offer_id, Assignment.staff_user_id)
        .join(Assignment, col(Assignment.plan_item_id) == col(PlanItem.id))
        .where(PlanItem.plan_id == plan_id)
        .order_by(col(PlanItem.id))
    ).all()
    for item_id, member_id, offer_id, staff_id in rows:
        if rng.random() < NO_ANSWER:
            outcome = "no_answer"
        elif rng.random() < FOLLOW_UP:
            outcome = "follow_up"
        else:
            stay = float(
                np.clip(1 - churn[member_id] + truth.get((member_id, offer_id), 0.0), 0, 1)
            )
            outcome = "accepted" if rng.random() < stay else "declined"
        contacts.log_outcome(session, staff[staff_id], item_id, outcome, None)


def _backdate(session: Session, plan_id: int) -> None:
    """Move the plan, its outcomes and its audit entries into the demo week."""
    plan = session.get(Plan, plan_id)
    plan.created_at, plan.approved_at = _at(0, 9), _at(0, 10)
    session.add(plan)
    item_ids = list(session.exec(select(PlanItem.id).where(PlanItem.plan_id == plan_id)).all())
    outcomes = session.exec(
        select(Outcome).where(col(Outcome.plan_item_id).in_(item_ids)).order_by(col(Outcome.id))
    ).all()
    when = {}
    for k, o in enumerate(outcomes):
        o.logged_at = _spread(k, len(outcomes))
        when[str(o.plan_item_id)] = o.logged_at
        session.add(o)
    entries = session.exec(
        select(AuditLog).where(
            (col(AuditLog.entity) == "plan") & (col(AuditLog.entity_id) == str(plan_id))
            | (col(AuditLog.entity) == "plan_item") & col(AuditLog.entity_id).in_(list(when))
        )
    ).all()
    stamps = {"plan.create": _at(0, 9), "plan.approve": _at(0, 10), "plan.assign": _at(0, 10, 5)}
    for e in entries:
        e.ts = stamps.get(e.action) or when.get(e.entity_id) or e.ts
        session.add(e)
    session.commit()

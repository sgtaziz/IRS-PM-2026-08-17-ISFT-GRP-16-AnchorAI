"""Build, save and read weekly plans: the pipeline behind /api/plan."""

import time
from datetime import datetime

from sqlmodel import Session, col, select

from anchorai.db import models
from anchorai.db.audit import record_audit
from anchorai.optimisation.baselines import greedy_uplift
from anchorai.optimisation.model import load_instance, violations
from anchorai.schemas import Plan, PlanItem, PlanRequest

SOLVERS = {"greedy": greedy_uplift}


class SavedPlan(Plan):
    """The shared `Plan` as stored, plus the fields the plan pages need to find it again."""

    id: int
    status: str
    created_at: datetime


class UnknownSolver(ValueError):
    pass


def build_plan(session: Session, user: models.User, req: PlanRequest) -> SavedPlan:
    """Run the planner for one week and save the result as a draft plan."""
    if req.solver not in SOLVERS:
        raise UnknownSolver(f"Unknown solver {req.solver!r}; available: {', '.join(SOLVERS)}")
    started = time.perf_counter()
    instance = load_instance(session)
    limits = instance.limits(req.budget, req.staff_minutes)
    chosen = SOLVERS[req.solver](instance.options, limits, None)
    broken = violations(chosen, instance.options, limits)
    if broken:
        raise RuntimeError(f"Solver {req.solver} returned an infeasible plan: {broken}")

    plan = models.Plan(
        week_start=req.as_of,
        request=req.model_dump(mode="json"),
        total_cost=float(chosen["cost"].sum()),
        total_staff_minutes=int(chosen["staff_minutes"].sum()),
        # Extra members the plan expects to keep, by its own uplift estimates.
        expected_members_retained=float(chosen["est_uplift"].sum()),
        created_by_id=user.id,
    )
    session.add(plan)
    session.flush()
    session.add_all(
        models.PlanItem(
            plan_id=plan.id,
            member_id=r.member_id,
            offer_id=r.offer_id,
            channel=r.channel,
            expected_value=float(r.value),
            explanation_id=f"p{plan.id}-{r.member_id}",
        )
        for r in chosen.itertuples()
    )
    summary = {
        "solver": req.solver,
        "budget": req.budget,
        "staff_minutes": req.staff_minutes,
        "contacts": len(chosen),
        "total_cost": plan.total_cost,
    }
    record_audit(session, user, "plan.create", "plan", str(plan.id), None, summary)
    session.commit()
    session.refresh(plan)
    stats = {
        "solver": req.solver,
        "uplift_source": "cbr",
        "options": len(instance.options),
        "seconds": round(time.perf_counter() - started, 2),
    }
    return _saved(session, plan, stats)


def latest_plan(session: Session) -> SavedPlan | None:
    """The plan for the latest week, newest first: the same one the assistant reads."""
    plan = session.exec(
        select(models.Plan).order_by(col(models.Plan.week_start).desc(), col(models.Plan.id).desc())
    ).first()
    return None if plan is None else _saved(session, plan)


def _saved(session: Session, plan: models.Plan, stats: dict | None = None) -> SavedPlan:
    rows = session.exec(
        select(models.PlanItem)
        .where(models.PlanItem.plan_id == plan.id, col(models.PlanItem.removed).is_(False))
        .order_by(col(models.PlanItem.expected_value).desc())
    ).all()
    return SavedPlan(
        id=plan.id,
        status=plan.status,
        created_at=plan.created_at,
        request=PlanRequest.model_validate(plan.request),
        items=[
            PlanItem(
                member_id=r.member_id,
                offer_id=r.offer_id,
                channel=r.channel,
                expected_value=r.expected_value,
                explanation_id=r.explanation_id,
            )
            for r in rows
        ],
        total_cost=plan.total_cost,
        total_staff_minutes=plan.total_staff_minutes,
        expected_members_retained=plan.expected_members_retained,
        solver_stats=stats or {},
    )

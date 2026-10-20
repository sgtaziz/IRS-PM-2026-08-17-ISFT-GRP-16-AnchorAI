"""Build, save and read weekly plans: the pipeline behind /api/plan."""

import time
from collections.abc import Callable
from datetime import datetime

from sqlmodel import Session, col, select

from anchorai import catalog
from anchorai.cbr.reasoner import uplift_series
from anchorai.db import models
from anchorai.db.audit import record_audit
from anchorai.discovery.scores import load_scores
from anchorai.optimisation.baselines import greedy_uplift
from anchorai.optimisation.contacts import app_case_base
from anchorai.optimisation.exact import exact
from anchorai.optimisation.explain import explain_plan, one_line
from anchorai.optimisation.ga import ga, load_cohorts
from anchorai.optimisation.model import load_instance, violations
from anchorai.schemas import Explanation, Plan, PlanItem, PlanRequest

SOLVERS = {"ga": ga, "exact": exact, "greedy": greedy_uplift}


class PlanRow(PlanItem):
    """The shared `PlanItem` plus a one-line reason for the plan table (W14)."""

    reason: str = ""


class SavedPlan(Plan):
    """The shared `Plan` as stored, plus the fields the plan pages need to find it again."""

    id: int
    status: str
    created_at: datetime
    items: list[PlanRow]


class UnknownSolver(ValueError):
    pass


Progress = Callable[[str, float], None]


def build_plan(
    session: Session, user: models.User, req: PlanRequest, progress: Progress | None = None
) -> SavedPlan:
    """Run the planner for one week and save the result as a draft plan."""
    report = progress or (lambda stage, done: None)
    if req.solver not in SOLVERS:
        raise UnknownSolver(f"Unknown solver {req.solver!r}; available: {', '.join(SOLVERS)}")
    started = time.perf_counter()
    report("loading", 0.0)
    case_base = app_case_base(session)
    instance = load_instance(session, uplift=uplift_series(case_base))
    limits = instance.limits(req.budget, req.staff_minutes)
    report("optimising", 0.05)
    extra = {}
    if req.solver == "ga":
        extra["on_generation"] = lambda gen, total: report("optimising", 0.05 + 0.85 * gen / total)
        extra["cohorts"] = load_cohorts(session)
    chosen = SOLVERS[req.solver](instance.options, limits, None, **extra)
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
    report("explaining", 0.9)
    session.add(plan)
    session.flush()
    ids = [f"p{plan.id}-{m}" for m in chosen["member_id"]]
    offer_names = {o.offer_id: o.name for o in catalog.list_offers(session)}
    explanations = explain_plan(
        chosen,
        ids,
        instance.outcomes,
        load_scores().set_index("member_id"),
        case_base,
        offer_names,
    )
    session.add_all(
        models.PlanItem(
            plan_id=plan.id,
            member_id=r.member_id,
            offer_id=r.offer_id,
            channel=r.channel,
            expected_value=float(r.value),
            explanation_id=e.explanation_id,
            explanation=e.model_dump(mode="json"),
        )
        for r, e in zip(chosen.itertuples(), explanations, strict=True)
    )
    summary = {
        "solver": req.solver,
        "budget": req.budget,
        "staff_minutes": req.staff_minutes,
        "contacts": len(chosen),
        "total_cost": plan.total_cost,
    }
    report("saving", 0.97)
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
            PlanRow(
                member_id=r.member_id,
                offer_id=r.offer_id,
                channel=r.channel,
                expected_value=r.expected_value,
                explanation_id=r.explanation_id,
                reason=one_line(r.explanation, r.offer_id),
            )
            for r in rows
        ],
        total_cost=plan.total_cost,
        total_staff_minutes=plan.total_staff_minutes,
        expected_members_retained=plan.expected_members_retained,
        solver_stats=stats or {},
    )


def explanation(session: Session, explanation_id: str) -> Explanation | None:
    item = session.exec(
        select(models.PlanItem).where(models.PlanItem.explanation_id == explanation_id)
    ).first()
    if item is None or item.explanation is None:
        return None
    return Explanation.model_validate(item.explanation)


def saved(session: Session, plan_id: int) -> SavedPlan:
    return _saved(session, session.get(models.Plan, plan_id))


def get_plan(session: Session, plan_id: int) -> SavedPlan | None:
    plan = session.get(models.Plan, plan_id)
    return None if plan is None else _saved(session, plan)


def previous_plan(session: Session, plan_id: int) -> SavedPlan | None:
    """The latest approved plan of an earlier week, for the week-on-week comparison (W15)."""
    current = session.get(models.Plan, plan_id)
    if current is None:
        return None
    before = session.exec(
        select(models.Plan)
        .where(models.Plan.status == "approved", col(models.Plan.id) != plan_id)
        .where(col(models.Plan.week_start) < current.week_start)
        .order_by(col(models.Plan.week_start).desc(), col(models.Plan.id).desc())
    ).first()
    return None if before is None else _saved(session, before)

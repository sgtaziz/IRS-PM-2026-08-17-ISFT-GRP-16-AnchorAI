"""Plan generation and planner comparison as one background job at a time (the GA takes about 25 s)."""

import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from sqlalchemy.engine import Engine
from sqlmodel import Session

from anchorai.cbr.reasoner import uplift_series
from anchorai.db import models
from anchorai.optimisation import service
from anchorai.optimisation.baselines import POLICIES
from anchorai.optimisation.contacts import app_case_base
from anchorai.optimisation.exact import solve_linear
from anchorai.optimisation.ga import build_problem, chosen, encode, load_cohorts, objective, run_ga
from anchorai.optimisation.model import load_instance, plan_value, violations
from anchorai.schemas import PlanRequest


@dataclass
class JobStatus:
    state: str = "idle"  # idle, running, done, failed
    kind: str | None = None  # plan or compare
    stage: str | None = None
    progress: float = 0.0
    started_at: str | None = None
    finished_at: str | None = None
    plan_id: int | None = None
    comparison: dict | None = None
    error: str | None = None
    request: dict = field(default_factory=dict)


_status = JobStatus()
_lock = threading.Lock()


class JobRunning(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def status() -> dict:
    return asdict(_status)


def _report(stage: str, done: float) -> None:
    _status.stage, _status.progress = stage, round(done, 3)


def _start(kind: str, req: PlanRequest, work: Callable[[], None]) -> dict:
    global _status
    with _lock:
        if _status.state == "running":
            raise JobRunning(f"A {_status.kind} job is already running")
        _status = JobStatus(
            "running", kind, "queued", 0.0, _now(), request=req.model_dump(mode="json")
        )

    def run() -> None:
        try:
            work()
            _status.state, _status.stage, _status.progress = "done", "done", 1.0
        except Exception as exc:  # noqa: BLE001  a thread must record any failure for the page
            _status.state, _status.error = "failed", str(exc)
        _status.finished_at = _now()

    threading.Thread(target=run, daemon=True).start()
    return status()


def start_plan(engine: Engine, user_id: int, req: PlanRequest) -> dict:
    """Build and save a plan in the background, on its own DB session."""
    if req.solver not in service.SOLVERS:
        raise service.UnknownSolver(f"Unknown solver {req.solver!r}")

    def work() -> None:
        with Session(engine) as session:
            user = session.get(models.User, user_id)
            _status.plan_id = service.build_plan(session, user, req, _report).id

    return _start("plan", req, work)


def compare(session: Session, req: PlanRequest, report=_report) -> dict:
    """Every planner on the same week's problem, scored by the planner's own estimates (W17)."""
    report("loading", 0.0)
    instance = load_instance(session, uplift=uplift_series(app_case_base(session)))
    options, limits = instance.options, instance.limits(req.budget, req.staff_minutes)
    plans = {name: policy(options, limits, 0) for name, policy in POLICIES.items()}
    report("optimising", 0.1)
    plans["exact"] = solve_linear(options, limits)[0]
    problem = build_problem(options, load_cohorts(), limits)
    start = encode(problem, options.index.get_indexer(plans["greedy-uplift"].index))
    genes, log, _ = run_ga(
        problem,
        limits,
        start,
        seed=0,
        on_generation=lambda g, n: report("optimising", 0.15 + 0.8 * g / n),
    )
    plans["ga"] = options.iloc[chosen(problem, genes)]
    rows = []
    for name, plan in plans.items():
        rows.append(
            {
                "planner": name,
                "contacts": len(plan),
                "spend": float(plan["cost"].sum()),
                "staff_minutes": int(plan["staff_minutes"].sum()),
                "linear_value": round(plan_value(plan), 2),
                "full_value": round(objective(problem, options.index.get_indexer(plan.index)), 2),
                "expected_extra_members": round(float(plan["est_uplift"].sum()), 2),
                "feasible": not violations(plan, options, limits),
            }
        )
    return {
        "request": req.model_dump(mode="json"),
        "planners": rows,
        "ga_convergence": log[["generation", "best", "mean"]].round(2).to_dict("records"),
    }


def start_compare(engine: Engine, req: PlanRequest) -> dict:
    def work() -> None:
        with Session(engine) as session:
            _status.comparison = compare(session, req)

    return _start("compare", req, work)

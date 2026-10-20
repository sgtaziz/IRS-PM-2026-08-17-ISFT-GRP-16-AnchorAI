"""Saved planner comparisons (W17): name the comparison just run, list, reopen and delete them."""

from sqlmodel import Session, col, select

from anchorai.db import models
from anchorai.db.audit import record_audit
from anchorai.optimisation import jobs


class NothingToSave(RuntimeError):
    pass


def _summary(s: models.Scenario) -> dict:
    planners = s.result.get("planners", [])
    best = max(planners, key=lambda r: r["full_value"], default=None)
    return {
        "id": s.id,
        "name": s.name,
        "created_at": s.created_at.isoformat(),
        "budget": s.request.get("budget"),
        "staff_minutes": s.request.get("staff_minutes"),
        "best_planner": best["planner"] if best else None,
        "best_extra_members": best["expected_extra_members"] if best else None,
    }


def save(session: Session, user: models.User, name: str) -> dict:
    """Save the comparison the server last ran; the browser only names it, so results can't be edited."""
    job = jobs.status()
    if job["kind"] != "compare" or job["state"] != "done" or not job["comparison"]:
        raise NothingToSave("Run a comparison first, then save it")
    comparison = job["comparison"]
    scenario = models.Scenario(
        name=name, request=comparison["request"], result=comparison, created_by_id=user.id
    )
    session.add(scenario)
    session.flush()
    after = {"name": name, **{k: comparison["request"][k] for k in ("budget", "staff_minutes")}}
    record_audit(session, user, "scenario.save", "scenario", str(scenario.id), None, after)
    session.commit()
    session.refresh(scenario)
    return _summary(scenario)


def list_saved(session: Session) -> list[dict]:
    rows = session.exec(select(models.Scenario).order_by(col(models.Scenario.created_at).desc()))
    return [_summary(s) for s in rows]


def get(session: Session, scenario_id: int) -> dict | None:
    s = session.get(models.Scenario, scenario_id)
    return None if s is None else {**_summary(s), "comparison": s.result}


def delete(session: Session, user: models.User, scenario_id: int) -> bool:
    s = session.get(models.Scenario, scenario_id)
    if s is None:
        return False
    record_audit(
        session, user, "scenario.delete", "scenario", str(scenario_id), {"name": s.name}, None
    )
    session.delete(s)
    session.commit()
    return True

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from anchorai.api.deps import SessionDep, require_role
from anchorai.db.models import User
from anchorai.discovery.service import DataNotBuilt
from anchorai.optimisation import assignment, jobs, overrides, service
from anchorai.reasoning.check import UnknownMember, UnknownOffer
from anchorai.reasoning.service import InvalidRuleBase
from anchorai.schemas import Channel, Explanation, PlanRequest

router = APIRouter()
Manager = Annotated[User, Depends(require_role("manager", "admin"))]


@router.post("", response_model=service.SavedPlan)
def build_plan(req: PlanRequest, session: SessionDep, user: Manager):
    try:
        return service.build_plan(session, user, req)
    except service.UnknownSolver as e:
        raise HTTPException(422, str(e)) from None
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    except FileNotFoundError:
        raise HTTPException(
            503, "Uplift estimates are missing: run `uv run anchorai data build`"
        ) from None
    except InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None


@router.get("/latest", response_model=service.SavedPlan)
def latest_plan(session: SessionDep):
    plan = service.latest_plan(session)
    if plan is None:
        raise HTTPException(404, "No plan yet")
    return plan


@router.post("/jobs", status_code=202)
def start_plan_job(req: PlanRequest, session: SessionDep, user: Manager) -> dict:
    """Generate a plan in the background; poll GET /api/plan/jobs/current."""
    try:
        return jobs.start_plan(session.get_bind(), user.id, req)
    except service.UnknownSolver as e:
        raise HTTPException(422, str(e)) from None
    except jobs.JobRunning as e:
        raise HTTPException(409, str(e)) from None


@router.post("/compare", status_code=202)
def start_compare(req: PlanRequest, session: SessionDep) -> dict:
    """Run every planner on the same week in the background (W17); poll GET /api/plan/jobs/current."""
    try:
        return jobs.start_compare(session.get_bind(), req)
    except jobs.JobRunning as e:
        raise HTTPException(409, str(e)) from None


@router.get("/jobs/current")
def current_job() -> dict:
    return jobs.status()


@router.get("/explanations/{explanation_id}", response_model=Explanation)
def explanation(explanation_id: str, session: SessionDep):
    found = service.explanation(session, explanation_id)
    if found is None:
        raise HTTPException(404, f"No explanation {explanation_id}")
    return found


class Reason(BaseModel):
    reason: str = Field(min_length=3)


class AddItem(Reason):
    member_id: str
    offer_id: str
    channel: Channel


def _override(call):
    try:
        return call()
    except overrides.PlanNotFound as e:
        raise HTTPException(404, f"No plan {e}") from None
    except overrides.PlanLocked as e:
        raise HTTPException(409, str(e)) from None
    except (UnknownMember, UnknownOffer) as e:
        raise HTTPException(404, f"Unknown {e}") from None
    except overrides.OverrideRejected as e:
        detail = f"{e}: {'; '.join(e.problems)}" if e.problems else str(e)
        raise HTTPException(422, detail) from None
    except assignment.NotApproved as e:
        raise HTTPException(409, str(e)) from None
    except assignment.CannotAssign as e:
        raise HTTPException(422, str(e)) from None


@router.get("/{plan_id}", response_model=service.SavedPlan)
def get_plan(plan_id: int, session: SessionDep):
    plan = service.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(404, f"No plan {plan_id}")
    return plan


@router.post("/{plan_id}/items", response_model=service.SavedPlan)
def add_item(plan_id: int, body: AddItem, session: SessionDep, user: Manager):
    _override(
        lambda: overrides.add_item(
            session, user, plan_id, body.member_id, body.offer_id, body.channel, body.reason
        )
    )
    return service.saved(session, plan_id)


@router.post("/{plan_id}/items/{member_id}/remove", response_model=service.SavedPlan)
def remove_item(plan_id: int, member_id: str, body: Reason, session: SessionDep, user: Manager):
    _override(lambda: overrides.remove_item(session, user, plan_id, member_id, body.reason))
    return service.saved(session, plan_id)


@router.post("/{plan_id}/approve", response_model=service.SavedPlan)
def approve(plan_id: int, session: SessionDep, user: Manager):
    _override(lambda: overrides.approve(session, user, plan_id))
    return service.saved(session, plan_id)


class Reassign(BaseModel):
    staff_user_id: int


@router.post("/{plan_id}/assign")
def assign(plan_id: int, session: SessionDep, user: Manager) -> dict:
    return _override(lambda: assignment.assign(session, user, plan_id))


@router.get("/{plan_id}/assignments")
def assignments(plan_id: int, session: SessionDep) -> dict:
    return _override(lambda: assignment.summary(session, plan_id))


@router.put("/{plan_id}/assignments/{member_id}")
def reassign(
    plan_id: int, member_id: str, body: Reassign, session: SessionDep, user: Manager
) -> dict:
    return _override(
        lambda: assignment.reassign(session, user, plan_id, member_id, body.staff_user_id)
    )


@router.get("/{plan_id}/call-sheet.csv", response_class=PlainTextResponse)
def call_sheet(plan_id: int, staff_id: int, session: SessionDep):
    text = assignment.call_sheet(session, plan_id, staff_id)
    disposition = f'attachment; filename="call-sheet-plan{plan_id}-staff{staff_id}.csv"'
    return PlainTextResponse(
        text, media_type="text/csv", headers={"Content-Disposition": disposition}
    )

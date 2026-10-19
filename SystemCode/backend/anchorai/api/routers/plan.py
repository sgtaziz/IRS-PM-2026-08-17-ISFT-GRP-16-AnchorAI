from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from anchorai.api.deps import SessionDep, require_role
from anchorai.db.models import User
from anchorai.discovery.service import DataNotBuilt
from anchorai.optimisation import service
from anchorai.reasoning.service import InvalidRuleBase
from anchorai.schemas import PlanRequest

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


@router.post("/compare")
def compare_policies(req: PlanRequest):
    raise HTTPException(501, "TODO Stream B: GA vs exact vs baselines on the same instance")


@router.get("/explanations/{explanation_id}")
def explanation(explanation_id: str):
    raise HTTPException(501, "TODO Stream B/C: Explanation for one plan item")

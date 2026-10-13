from fastapi import APIRouter, HTTPException

from anchorai.schemas import Plan, PlanRequest

router = APIRouter()


@router.post("", response_model=Plan)
def build_plan(req: PlanRequest):
    raise HTTPException(501, "TODO Stream B: rules -> CBR uplift -> optimiser -> Plan")


@router.post("/compare")
def compare_policies(req: PlanRequest):
    raise HTTPException(501, "TODO Stream B: GA vs exact vs baselines on the same instance")


@router.get("/explanations/{explanation_id}")
def explanation(explanation_id: str):
    raise HTTPException(501, "TODO Stream B/C: Explanation for one plan item")

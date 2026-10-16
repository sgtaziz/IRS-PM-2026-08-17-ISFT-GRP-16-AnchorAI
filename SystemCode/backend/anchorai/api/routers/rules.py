from fastapi import APIRouter, Depends, HTTPException

from anchorai.api.deps import SessionDep, require_role
from anchorai.discovery.service import DataNotBuilt
from anchorai.reasoning import service
from anchorai.reasoning.models import RuleOutcome
from anchorai.reasoning.service import RuleSet

router = APIRouter()


@router.get("", response_model=RuleSet, dependencies=[Depends(require_role("admin"))])
def list_rules(session: SessionDep):
    try:
        return service.rule_set(session)
    except service.InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None


@router.put("/{rule_id}", dependencies=[Depends(require_role("admin"))])
def update_rule(rule_id: str, rule: dict):
    raise HTTPException(501, "Rule editing arrives with the rules admin page (W40)")


@router.get("/trace/{member_id}", response_model=RuleOutcome)
def trace(member_id: str, session: SessionDep):
    try:
        outcome = service.trace(session, member_id)
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    except service.InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None
    if outcome is None:
        raise HTTPException(404, f"Unknown member {member_id}")
    return outcome

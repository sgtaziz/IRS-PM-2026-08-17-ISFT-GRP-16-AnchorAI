from fastapi import APIRouter, Depends, HTTPException

from anchorai.api.deps import require_role

router = APIRouter()


@router.get("")
def list_rules():
    raise HTTPException(501, "TODO Stream C: load reasoning/rules/*.yaml")


@router.put("/{rule_id}", dependencies=[Depends(require_role("admin"))])
def update_rule(rule_id: str, rule: dict):
    raise HTTPException(501, "TODO Stream C: validate + save rule, return conflicts found")


@router.post("/trace/{member_id}")
def trace(member_id: str):
    raise HTTPException(501, "TODO Stream C: run engine for one member, return RuleFiring list")

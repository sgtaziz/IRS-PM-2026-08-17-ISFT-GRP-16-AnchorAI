"""Plan routes every role may read (Member 360 is read by staff too); /api/plan itself is manager-only."""

from fastapi import APIRouter, HTTPException

from anchorai import catalog
from anchorai.api.deps import SessionDep
from anchorai.cbr.reasoner import load_case_base
from anchorai.optimisation.explain import member_evidence

router = APIRouter()


@router.get("/similar-cases/{member_id}")
def similar_cases(member_id: str, session: SessionDep) -> list[dict]:
    case_base = load_case_base()
    if member_id not in case_base.x.index:
        raise HTTPException(404, f"Unknown member {member_id}")
    names = {o.offer_id: o.name for o in catalog.list_offers(session, active_only=True)}
    return [e for e in member_evidence(case_base, member_id, names) if e["offer_id"] in names]

from fastapi import APIRouter, HTTPException

from anchorai.api.deps import SessionDep
from anchorai.discovery import service as member_data
from anchorai.optimisation import contacts

router = APIRouter()


@router.get("")
def contact_history(member_id: str, session: SessionDep) -> list[dict]:
    try:
        known = member_id in member_data.get_data().table.index
    except member_data.DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    if not known:
        raise HTTPException(404, f"Unknown member {member_id}")
    return contacts.history(session, member_id)

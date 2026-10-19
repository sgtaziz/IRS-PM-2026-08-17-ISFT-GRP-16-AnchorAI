from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from anchorai.api.deps import CurrentUser, SessionDep
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


class LogOutcome(BaseModel):
    plan_item_id: int
    outcome: Literal["reached", "no_answer", "accepted", "declined", "follow_up"]
    note: str | None = Field(default=None, max_length=500)


@router.post("")
def log_outcome(body: LogOutcome, session: SessionDep, user: CurrentUser) -> dict:
    try:
        return contacts.log_outcome(session, user, body.plan_item_id, body.outcome, body.note)
    except contacts.UnknownContact as e:
        raise HTTPException(404, str(e)) from None
    except contacts.NotYours as e:
        raise HTTPException(403, str(e)) from None

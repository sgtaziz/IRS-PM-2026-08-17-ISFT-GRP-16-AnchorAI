from fastapi import APIRouter, HTTPException

from anchorai.api.deps import SessionDep
from anchorai.assistant import drafts
from anchorai.assistant.drafts import Draft, DraftIn
from anchorai.discovery.service import DataNotBuilt
from anchorai.reasoning import check, service

router = APIRouter()


@router.post("", response_model=Draft)
def make_draft(body: DraftIn, session: SessionDep):
    try:
        return drafts.make_draft(session, body)
    except check.UnknownMember as e:
        raise HTTPException(404, f"Unknown member {e}") from None
    except check.UnknownOffer as e:
        raise HTTPException(422, f"Unknown offer {e}") from None
    except drafts.OfferUnavailable as e:
        raise HTTPException(409, str(e)) from None
    except drafts.OfferBlocked as e:
        raise HTTPException(409, f"This offer is blocked for this member: {e}") from None
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    except service.InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None

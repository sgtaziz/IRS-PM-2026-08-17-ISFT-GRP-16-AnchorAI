from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from anchorai.api.deps import CurrentUser, SessionDep
from anchorai.assistant import service
from anchorai.assistant.service import AssistantReply, FeedbackIn, HistoryTurn
from anchorai.discovery.service import DataNotBuilt

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # The member open on the current page, used when the question doesn't name one.
    member_id: str | None = Field(default=None, pattern=r"^M\d{4}$")
    # Earlier turns of this chat, oldest first. The browser keeps them; a refresh starts over.
    history: list[HistoryTurn] = Field(default=[], max_length=10)


@router.post("/chat", response_model=AssistantReply)
def chat(req: ChatRequest, session: SessionDep, user: CurrentUser):
    try:
        return service.answer(
            session, req.message, req.member_id, role=user.role, history=req.history
        )
    except (DataNotBuilt, service.AssistantUnavailable) as e:
        raise HTTPException(503, str(e)) from None


class FeedbackOut(BaseModel):
    id: int


@router.post("/feedback", response_model=FeedbackOut)
def feedback(fb: FeedbackIn, session: SessionDep, user: CurrentUser):
    return FeedbackOut(id=service.save_feedback(session, user, fb).id)

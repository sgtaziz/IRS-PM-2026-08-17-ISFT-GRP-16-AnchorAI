from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/chat")
def chat(req: ChatRequest):
    raise HTTPException(501, "TODO Stream C: intent -> slots -> tool -> grounded LLM answer")

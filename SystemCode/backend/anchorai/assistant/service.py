"""The assistant pipeline: intent -> slots -> deterministic tool -> grounded LLM answer."""

import logging
from collections.abc import Callable
from typing import Literal

from openai import OpenAIError
from pydantic import BaseModel, Field
from sqlmodel import Session

from anchorai.assistant import llm
from anchorai.assistant.classifier import UNKNOWN, IntentClassifier, get_classifier
from anchorai.assistant.prompt import DONT_KNOW, build_messages
from anchorai.assistant.slots import Slots
from anchorai.assistant.tools import TOOLS, Evidence
from anchorai.db.audit import record_audit
from anchorai.db.models import AssistantFeedback, User

log = logging.getLogger(__name__)
Chat = Callable[[list[dict]], str]
# Plan figures are manager-only in the API (PLAN 8.1); the assistant must not leak them to staff.
MANAGER_INTENTS = {"plan_summary", "what_if_budget"}


class AssistantUnavailable(RuntimeError):
    pass


class AssistantReply(BaseModel):
    intent: str
    score: float
    slots: Slots
    tool: str | None
    evidence: list[Evidence]
    answer: str
    # False when nothing grounded the answer (unknown intent, missing data, service not ready).
    grounded: bool
    llm_used: bool


class FeedbackIn(BaseModel):
    message: str = Field(max_length=1000)
    answer: str = Field(max_length=4000)
    intent: str | None = Field(default=None, max_length=50)
    tool: str | None = Field(default=None, max_length=50)
    rating: Literal[1, -1]
    comment: str | None = Field(default=None, max_length=1000)


def _template(evidence: list[Evidence]) -> str:
    return " ".join(f"{e.text} [{e.id}]." for e in evidence)


def answer(
    session: Session,
    message: str,
    context_member_id: str | None = None,
    role: str = "staff",
    classifier: IntentClassifier | None = None,
    chat: Chat = llm.chat,
) -> AssistantReply:
    try:
        classifier = classifier or get_classifier()
    except OSError as e:
        # The embedding model isn't downloaded and there's no network to fetch it.
        raise AssistantUnavailable(f"Intent model unavailable: {e}") from e
    prediction = classifier.classify(message, context_member_id)
    reply = AssistantReply(
        intent=prediction.intent,
        score=prediction.score,
        slots=prediction.slots,
        tool=None,
        evidence=[],
        answer=DONT_KNOW,
        grounded=False,
        llm_used=False,
    )
    if prediction.intent == UNKNOWN:
        return reply

    if prediction.intent in MANAGER_INTENTS and role == "staff":
        reply.answer = "Plan details are only available to managers."
        return reply

    result = TOOLS[prediction.intent](session, prediction.slots)
    reply.tool, reply.evidence = result.tool, result.evidence
    if not result.evidence:
        reply.answer = result.note or DONT_KNOW
        return reply

    reply.grounded = True
    try:
        reply.answer = chat(build_messages(message, result.evidence)).strip() or DONT_KNOW
        reply.llm_used = True
    except (OpenAIError, IndexError, AttributeError) as e:
        # LLM down or misconfigured: still answer, straight from the evidence.
        log.warning("assistant LLM unavailable, using template answer: %s", e)
        reply.answer = _template(result.evidence)
    return reply


def save_feedback(session: Session, user: User, feedback: FeedbackIn) -> AssistantFeedback:
    row = AssistantFeedback(user_id=user.id, **feedback.model_dump())
    session.add(row)
    session.flush()
    record_audit(
        session,
        user,
        "assistant_feedback",
        "assistant_feedback",
        str(row.id),
        after=feedback.model_dump(),
    )
    session.commit()
    return row

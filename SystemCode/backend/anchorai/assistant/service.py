"""The assistant pipeline: intent -> slots -> deterministic tool -> grounded LLM answer."""

import logging
import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

from openai import OpenAIError
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session

from anchorai.assistant import llm
from anchorai.assistant.classifier import (
    UNKNOWN,
    WRITE_REQUEST,
    IntentClassifier,
    get_classifier,
)
from anchorai.assistant.prompt import DONT_KNOW, build_messages
from anchorai.assistant.slots import Slots, extract_slots
from anchorai.assistant.tools import TOOLS, Evidence
from anchorai.db.audit import record_audit
from anchorai.db.models import AssistantFeedback, User

log = logging.getLogger(__name__)
Chat = Callable[[list[dict]], str]
ChatStream = Callable[[list[dict]], Iterator[str]]
# Plan figures are manager-only in the API (PLAN 8.1); the assistant must not leak them to staff.
MANAGER_INTENTS = {"plan_summary", "what_if_budget"}
MEMBER_ID = re.compile(r"M\d{4}")
# Without these, an unrecognised message ("thanks", "tell me a joke") is just not understood,
# rather than a follow-up to the previous answer.
FOLLOW_UP_CUES = re.compile(
    r"\b(they|them|their|theirs|he|him|his|she|her|it|its|that|this|those|these|why|how come"
    r"|more|explain|elaborate|clarify|simpl\w*|mean|detail\w*|again|else|also|instead"
    r"|what about|how about|and)\b",
    re.IGNORECASE,
)


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
    # True when the question had no intent of its own and continued the previous turn's.
    follow_up: bool = False


class FeedbackIn(BaseModel):
    message: str = Field(max_length=1000)
    answer: str = Field(max_length=4000)
    intent: str | None = Field(default=None, max_length=50)
    tool: str | None = Field(default=None, max_length=50)
    rating: Literal[1, -1]
    comment: str | None = Field(default=None, max_length=1000)


class HistoryTurn(BaseModel):
    question: str = Field(max_length=1000)
    answer: str = Field(max_length=4000)
    intent: str = Field(max_length=50)
    slots: Slots = Slots()

    @field_validator("slots")
    @classmethod
    def _bounded(cls, slots: Slots) -> Slots:
        lists = (slots.member_ids, slots.instructor_ids, slots.class_ids)
        if any(len(ids) > 10 or any(len(i) > 10 for i in ids) for ids in lists):
            raise ValueError("too many or too long ids")
        if not all(MEMBER_ID.fullmatch(m) for m in slots.member_ids):
            raise ValueError("member ids look like M0001")
        return slots


def _template(evidence: list[Evidence]) -> str:
    return "\n".join(f"- {e.text} [{e.id}]" for e in evidence)


def _previous(history: Sequence[HistoryTurn], classifier: IntentClassifier) -> HistoryTurn | None:
    """The turn a follow-up continues (only the last one), with the client's ids checked."""
    if not history or history[-1].intent not in TOOLS:
        return None
    turn = history[-1]
    slots = turn.slots.model_copy()
    slots.instructor_ids = [i for i in slots.instructor_ids if i in classifier.instructors.values()]
    slots.class_ids = [c for c in slots.class_ids if c in classifier.classes.values()]
    return turn.model_copy(update={"slots": slots})


@dataclass
class Prepared:
    """Everything up to the LLM call. `messages` is None when the reply is already final."""

    reply: AssistantReply
    messages: list[dict] | None = None
    # What to answer when the LLM is unavailable.
    fallback: str = DONT_KNOW


def prepare(
    session: Session,
    message: str,
    context_member_id: str | None = None,
    role: str = "staff",
    history: Sequence[HistoryTurn] = (),
    classifier: IntentClassifier | None = None,
) -> Prepared:
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
    named = False
    if (
        prediction.intent == UNKNOWN
        and not WRITE_REQUEST.search(message)
        and (previous := _previous(history, classifier))
    ):
        # "What about M0002?" or "explain that more simply": continue the previous question,
        # with whatever the new message names, else the previous turn's members and entities.
        slots = extract_slots(message, classifier.instructors, classifier.classes)[0]
        named = bool(
            slots.member_ids or slots.instructor_ids or slots.class_ids or slots.amount is not None
        )
        if not named:
            slots = previous.slots
        if (named or FOLLOW_UP_CUES.search(message)) and classifier.accepts(
            previous.intent, len(slots.member_ids)
        ):
            reply.intent, reply.slots, reply.follow_up = previous.intent, slots, True
    if reply.intent == UNKNOWN:
        return Prepared(reply)

    if reply.intent in MANAGER_INTENTS and role == "staff":
        reply.answer = "Plan details are only available to managers."
        return Prepared(reply)

    result = TOOLS[reply.intent](session, reply.slots)
    if role == "staff":
        # Plan lines come last in every tool, so dropping them keeps the E-numbers contiguous.
        result.evidence = [e for e in result.evidence if e.kind != "plan"]
    reply.tool, reply.evidence = result.tool, result.evidence
    if not result.evidence:
        reply.answer = result.note or DONT_KNOW
        return Prepared(reply)

    reply.grounded = True
    pairs = [(t.question, t.answer) for t in history]
    # Without the LLM, answer straight from the evidence, unless the question was a clarification
    # only the LLM could rephrase.
    if reply.follow_up and not named:
        fallback = "I can't answer follow-up questions while the language model is offline."
    else:
        fallback = _template(result.evidence)
    return Prepared(reply, build_messages(message, result.evidence, pairs), fallback)


def answer(
    session: Session,
    message: str,
    context_member_id: str | None = None,
    role: str = "staff",
    history: Sequence[HistoryTurn] = (),
    classifier: IntentClassifier | None = None,
    chat: Chat = llm.chat,
) -> AssistantReply:
    """`history` is the chat so far, oldest first; it is kept by the client, not the server."""
    prepared = prepare(session, message, context_member_id, role, history, classifier)
    reply = prepared.reply
    if prepared.messages is None:
        return reply
    try:
        reply.answer = chat(prepared.messages).strip() or DONT_KNOW
        reply.llm_used = True
    except (OpenAIError, IndexError, AttributeError) as e:
        log.warning("assistant LLM unavailable, using template answer: %s", e)
        reply.answer = prepared.fallback
    return reply


def stream_answer(
    session: Session,
    message: str,
    context_member_id: str | None = None,
    role: str = "staff",
    history: Sequence[HistoryTurn] = (),
    classifier: IntentClassifier | None = None,
    chat_stream: ChatStream | None = None,
) -> Iterator[tuple[str, dict]]:
    """Events for the SSE endpoint: one `meta`, then `delta`s of the answer text, then `done`.

    The tools run before this returns, while the caller's session is still open; the LLM is only
    called as the events are read.
    """
    prepared = prepare(session, message, context_member_id, role, history, classifier)
    return _events(prepared, chat_stream or llm.chat_stream)


def _events(prepared: Prepared, chat_stream: ChatStream) -> Iterator[tuple[str, dict]]:
    reply = prepared.reply
    yield "meta", reply.model_dump(exclude={"answer", "grounded", "llm_used"})
    if prepared.messages is None:
        yield "delta", {"text": reply.answer}
        yield "done", {"grounded": False, "llm_used": False, "answer": reply.answer}
        return
    parts: list[str] = []
    pieces = chat_stream(prepared.messages)
    try:
        for piece in pieces:
            parts.append(piece)
            yield "delta", {"text": piece}
    except Exception as e:  # noqa: BLE001 - any LLM or network failure degrades to the template
        log.warning("assistant LLM failed, using template answer: %s", e)
        parts = []
    finally:
        # A client that disconnects closes this generator; stop reading from the LLM too.
        close = getattr(pieces, "close", None)
        if close:
            close()
    # `done` carries the final text and replaces whatever was streamed. When the LLM fails, even
    # midway, the template goes only here, never as a delta appended to a partial answer.
    if parts:
        answer_text = "".join(parts).strip() or DONT_KNOW
    else:
        answer_text = prepared.fallback
    yield "done", {"grounded": True, "llm_used": bool(parts), "answer": answer_text}


def save_feedback(session: Session, user: User, feedback: FeedbackIn) -> AssistantFeedback:
    row = AssistantFeedback(user_id=user.id, **feedback.model_dump())
    session.add(row)
    session.flush()
    record_audit(
        session,
        user,
        "assistant.feedback",
        "assistant_feedback",
        str(row.id),
        after=feedback.model_dump(),
    )
    session.commit()
    return row

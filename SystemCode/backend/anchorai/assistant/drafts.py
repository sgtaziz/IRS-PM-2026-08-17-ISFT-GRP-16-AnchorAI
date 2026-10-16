"""Member message drafts: grounded LLM text with a deterministic template behind it.

Nothing here sends anything; staff copy the text into their own messaging tool.
"""

import logging
import re
from typing import Literal

from openai import OpenAIError
from pydantic import BaseModel
from sqlmodel import Session

from anchorai import catalog
from anchorai.assistant.llm import chat
from anchorai.reasoning import service as reasoning
from anchorai.reasoning.check import ItemCheck, ProposedItem, check_items
from anchorai.schemas import Channel

log = logging.getLogger(__name__)

SMS_LIMIT = 300
# Internal scoring and retention framing are for staff; they must never reach a member.
FORBIDDEN = re.compile(
    r"\b(churn\w*|at[- ]risk|risk\w*|score\w*|probabilit\w*|model|algorithm|"
    r"leav\w*|quit\w*|slipping|high[- ]value|cancel\w* your (membership|contract))\b",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(r"\[[^\]]*\]|\{[^}]*\}")
NUMBER = re.compile(r"\d+(?:\.\d+)?")

CHANNEL_STYLE = {
    "sms": f"A text message of at most {SMS_LIMIT - 40} characters. No subject, no emojis.",
    "email": "An email of 60-110 words. The first line is 'Subject: ' followed by a short subject.",
    "call": "A phone call script of 5-8 short lines: opening, reason, offer, ask, close.",
    "in_person": "4-6 short '- ' bullet talking points written for the staff member to say "
    "face to face, not a script addressed to the member.",
}
SYSTEM = """You write short messages from a gym's staff to one member, in a warm, friendly tone.
Use ONLY the facts in the evidence lines. Never invent prices, dates, discounts, guarantees or
conditions that are not in them. Offer exactly the offer in the evidence and nothing more.
Never say the member may leave, is at risk or has a score; never mention data, models or tracking.
Do not use a name or placeholders such as [Name]; start with a plain greeting.
Reply with the message only."""


class DraftIn(BaseModel):
    member_id: str
    offer_id: str
    channel: Channel


class Draft(BaseModel):
    text: str
    subject: str | None = None
    channel: Channel
    source: Literal["llm", "template"]
    evidence: list[str]


class OfferUnavailable(RuntimeError):
    pass


class OfferBlocked(RuntimeError):
    def __init__(self, check: ItemCheck):
        super().__init__("; ".join(v.description for v in check.violations))
        self.check = check


def _evidence(session: Session, member_id: str, offer_id: str, channel: Channel) -> list[str]:
    facts = reasoning.all_facts()[member_id]
    offer = next(o for o in catalog.list_offers(session) if o.offer_id == offer_id)
    lines = [
        f"Offer: {offer.name}",
        f"Who it is for: {offer.eligibility or 'members'}",
        f"Channel: {channel.value.replace('_', ' ')}",
    ]
    months = int(facts["lifetime"])
    lines.append(
        f"The member has been with the gym for {months} month{'s' if months != 1 else ''}"
        if months
        else "The member joined very recently"
    )
    if facts.get("group_visits") == 1:
        lines.append("The member attends group classes")
    if facts.get("lost_anchor_instructor"):
        lines.append("An instructor the member often trains with has left the gym")
    if facts.get("class_cancelled"):
        lines.append("A class the member attends has been cancelled")
    return lines


def _template(session: Session, member_id: str, offer_id: str, channel: Channel) -> Draft:
    facts = reasoning.all_facts()[member_id]
    offer = next(o for o in catalog.list_offers(session) if o.offer_id == offer_id)
    months = int(facts["lifetime"])
    thanks = (
        f"Thank you for {months} month{'s' if months != 1 else ''} with us."
        if months
        else "Welcome to the gym."
    )
    change = ""
    if facts.get("lost_anchor_instructor"):
        change = "We know a familiar instructor has moved on, and we'd like to help you settle in."
    elif facts.get("class_cancelled"):
        change = "We're sorry a class you enjoy has been cancelled."
    eligibility = f" ({offer.eligibility.rstrip('.')})" if offer.eligibility else ""
    ask = {
        "sms": "Reply here or ask at the front desk to take it up.",
        "email": "Just reply to this email or ask at the front desk and we'll set it up.",
        "call": "Would you like to take this up?",
        "in_person": "Ask if they would like to take it up today.",
    }[channel.value]
    evidence = _evidence(session, member_id, offer_id, channel)
    subject = None

    if channel is Channel.SMS:
        text = f"Hi! {thanks} We'd like to offer you: {offer.name}{eligibility}. {ask}"
        if len(text) > SMS_LIMIT:
            text = f"Hi! We'd like to offer you: {offer.name}. {ask}"
    elif channel is Channel.EMAIL:
        subject = f"Something for you: {offer.name}"
        parts = [
            "Hi,",
            " ".join(p for p in (thanks, change) if p),
            f"We'd like to offer you: {offer.name}{eligibility}.",
            ask,
            "Best wishes,\nYour gym team",
        ]
        text = "\n\n".join(p for p in parts if p)
    elif channel is Channel.CALL:
        lines = [
            "Hi, this is from your gym. Do you have a minute?",
            thanks,
            change,
            f"We'd like to offer you: {offer.name}{eligibility}.",
            ask,
            "Thanks for your time, and see you at the gym.",
        ]
        text = "\n".join(line for line in lines if line)
    else:
        lines = [
            thanks,
            change,
            f"Offer: {offer.name}{eligibility}.",
            "Mention only what the offer includes; don't promise anything extra.",
            ask,
        ]
        text = "\n".join(f"- {line}" for line in lines if line)
    return Draft(text=text, subject=subject, channel=channel, source="template", evidence=evidence)


def _split_subject(text: str) -> tuple[str | None, str]:
    first, _, rest = text.partition("\n")
    if first.lower().startswith("subject:"):
        return first.split(":", 1)[1].strip(), rest.strip()
    return None, text


def _acceptable(text: str, evidence: list[str], channel: Channel) -> bool:
    allowed = set(NUMBER.findall(" ".join(evidence)))
    if (
        not text
        or FORBIDDEN.search(text)
        or PLACEHOLDER.search(text)
        or not set(NUMBER.findall(text)) <= allowed
    ):
        return False
    return channel is not Channel.SMS or len(text) <= SMS_LIMIT


def _llm(evidence: list[str], channel: Channel) -> Draft | None:
    block = "\n".join(f"- {line}" for line in evidence)
    try:
        raw = chat(
            [
                {"role": "system", "content": SYSTEM},
                {
                    "role": "user",
                    "content": f"Format: {CHANNEL_STYLE[channel.value]}\n\nEvidence:\n{block}",
                },
            ],
            temperature=0.4,
        ).strip()
    except (OpenAIError, IndexError, AttributeError) as e:
        log.warning("draft LLM unavailable, using template: %s", e)
        return None
    subject, text = _split_subject(raw) if channel is Channel.EMAIL else (None, raw)
    if not _acceptable(f"{subject or ''} {text}".strip(), evidence, channel) or (
        channel is Channel.EMAIL and not subject
    ):
        log.warning("draft LLM output rejected, using template")
        return None
    return Draft(text=text, subject=subject, channel=channel, source="llm", evidence=evidence)


def make_draft(session: Session, req: DraftIn, use_llm: bool = True) -> Draft:
    """Raises UnknownMember / UnknownOffer (from the guardrail check), OfferUnavailable or OfferBlocked.

    Every channel must be one the offer's catalogue entry lists, call and in person included."""
    check = check_items(session, [ProposedItem(**req.model_dump())])[0]
    if not check.offer_active:
        raise OfferUnavailable("This offer is not active")
    if not check.channel_offered:
        raise OfferUnavailable(f"This offer is not available by {req.channel.value}")
    if not check.allowed:
        raise OfferBlocked(check)
    template = _template(session, req.member_id, req.offer_id, req.channel)
    if use_llm and (draft := _llm(template.evidence, req.channel)):
        return draft
    return template

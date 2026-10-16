"""Slot filling: member ids, money, instructors and classes, from notebooks/c_intent_classifier.ipynb."""

import re

from pydantic import BaseModel

# Each pattern captures (number, optional suffix). All amounts are taken out before member ids are
# matched, so "budget drops to 1000" or "$2000" never turn into a member id.
MONEY = [
    re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(k)?\b", re.IGNORECASE),
    re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\s*(k|dollars?|usd)\b", re.IGNORECASE),
    re.compile(
        r"(?<=\bbudget)(?:\s+(?:of|to|is|was|were|at|drops|goes|falls|rises|cut|of only)){0,3}"
        r"\s+(\d[\d,]*)()\b",
        re.IGNORECASE,
    ),
]
MEMBER = re.compile(r"\b(?:m|member\s*#?\s*)(\d{1,4})\b|\b(\d{2,4})\b", re.IGNORECASE)


class Slots(BaseModel):
    member_ids: list[str] = []
    amount: float | None = None
    instructor_ids: list[str] = []
    class_ids: list[str] = []


def _take_amounts(text: str) -> tuple[list[float], str]:
    amounts: list[float] = []

    def grab(match: re.Match) -> str:
        value = float(match.group(1).replace(",", ""))
        amounts.append(value * 1000 if (match.group(2) or "").lower() == "k" else value)
        return " AMOUNT "

    for pattern in MONEY:
        text = pattern.sub(grab, text)
    return amounts, text


def extract_slots(
    text: str, instructors: dict[str, str], classes: dict[str, str]
) -> tuple[Slots, str]:
    """Slots plus the text with each slot replaced by a placeholder, which is what gets embedded.

    `instructors` and `classes` map display names to ids.
    """
    slots = Slots()
    amounts, rest = _take_amounts(text)
    slots.amount = amounts[0] if amounts else None
    for full, iid in instructors.items():
        for name in (full, full.split()[0]):
            if re.search(rf"\b{re.escape(name)}\b", rest, re.IGNORECASE):
                slots.instructor_ids.append(iid)
                rest = re.sub(
                    rf"\b{re.escape(name)}('s)?\b", " INSTRUCTOR ", rest, flags=re.IGNORECASE
                )
                break
    for name, cid in classes.items():
        # Class names are common words ("Core", "Step"), so need the word "class" or a capital.
        named = re.search(
            rf"\b{re.escape(name)}\b(?=.*\bclass)|\bclass\b.*\b{re.escape(name)}\b",
            rest,
            re.IGNORECASE,
        )
        if named or re.search(rf"\b{re.escape(name)}\b", rest):
            slots.class_ids.append(cid)
            rest = re.sub(rf"\b{re.escape(name)}\b", " CLASS ", rest, flags=re.IGNORECASE)
    for m in MEMBER.finditer(rest):
        member_id = f"M{int(m.group(1) or m.group(2)):04d}"
        if member_id not in slots.member_ids:
            slots.member_ids.append(member_id)
    rest = MEMBER.sub(" MEMBER ", rest)
    return slots, re.sub(r"\s+", " ", rest).strip()

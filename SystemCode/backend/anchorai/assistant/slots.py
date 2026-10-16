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
MEMBER = re.compile(r"\b(?:m|member\s*#?\s*|#)(\d{1,4})\b|\b(\d{2,4})\b", re.IGNORECASE)
# A bare number is a member id ("why 1043 but not 2210?") unless its context says otherwise.
NOT_MEMBER_BEFORE = re.compile(
    r"\b(top|week|weeks|last|next|past|in|since|until|about|around|of)\s*$", re.IGNORECASE
)
NOT_MEMBER_AFTER = re.compile(
    r"^\s*(%|percent|months?|weeks?|days?|years?|hours?|minutes?|mins?|am|pm|members|people"
    r"|classes|visits|times|calls|offers)\b",
    re.IGNORECASE,
)
WORD_NUMBERS = {"three": 3, "five": 5, "ten": 10, "fifteen": 15, "twenty": 20}
_COUNT = "|".join(["\\d{1,3}", *WORD_NUMBERS])
# "top 10", "first five", "10 riskiest"; the number is taken out so it never reads as a member id.
COUNT = [
    re.compile(rf"\b(?:top|first|next|worst|riskiest|highest)\s+({_COUNT})\b", re.IGNORECASE),
    re.compile(rf"\b({_COUNT})\s+(?:highest|riskiest|worst|top|most)\b", re.IGNORECASE),
    re.compile(rf"\b({_COUNT})\s+(?:members|people|customers)\b", re.IGNORECASE),
]
CLUB = re.compile(r"\bclub\s+(C\d{1,2})\b|\b(C\d{1,2})\b", re.IGNORECASE)
RISK_BAND = re.compile(r"\b(high|medium|low)[\s-]+risk\b", re.IGNORECASE)
NEW_MEMBERS = re.compile(
    r"\bnew(?:er|est)?\s+(?:members?|joiners?|people|customers)\b|\b(?:recently|just)\s+joined\b",
    re.IGNORECASE,
)
# Substrings of the segment names in the member table; resolved against the real names by the tool.
SEGMENT_WORDS = re.compile(
    r"\b(new and slipping|loyalists?|solo trainers?|class[\s-]goers?)\b", re.IGNORECASE
)
YEAR = re.compile(r"^(19|20)\d\d$")


class Slots(BaseModel):
    member_ids: list[str] = []
    amount: float | None = None
    instructor_ids: list[str] = []
    class_ids: list[str] = []
    limit: int | None = None
    risk_band: str | None = None
    segment: str | None = None
    club_id: str | None = None
    new_members: bool = False


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

    def take_count(match: re.Match) -> str:
        word = match.group(1).lower()
        slots.limit = WORD_NUMBERS.get(word) or int(word)
        return match.group(0).replace(match.group(1), " COUNT ")

    if not slots.amount:
        for pattern in COUNT:
            if pattern.search(rest):
                rest = pattern.sub(take_count, rest, count=1)
                break

    if club := CLUB.search(rest):
        slots.club_id = (club.group(1) or club.group(2)).upper()
        rest = CLUB.sub(" CLUB ", rest)
    if band := RISK_BAND.search(rest):
        slots.risk_band = band.group(1).lower()
    if NEW_MEMBERS.search(rest):
        slots.new_members = True
    if segment := SEGMENT_WORDS.search(rest):
        slots.segment = re.sub(r"[\s-]+", " ", segment.group(1).lower())
        rest = SEGMENT_WORDS.sub(" SEGMENT ", rest)

    for full, iid in instructors.items():
        # Full names in any case; a first name only when capitalised ("Sam", not "sam" or "lee").
        first = re.escape(full.split()[0])
        for pattern in (
            re.compile(rf"\b{re.escape(full)}('s)?\b", re.IGNORECASE),
            re.compile(rf"\b{first}('s)?\b"),
        ):
            if pattern.search(rest):
                slots.instructor_ids.append(iid)
                rest = pattern.sub(" INSTRUCTOR ", rest)
                break

    for name, cid in classes.items():
        # Class names are common words ("Core", "Step"): need "<name> class", or a capital
        # anywhere but the start of the question.
        n = re.escape(name)
        named = re.search(
            rf"\b{n}\s+class(es)?\b|\bclass(es)?\s+(called\s+)?{n}\b", rest, re.IGNORECASE
        )
        capital = re.search(rf"\S\s+{n}\b", rest)
        if named or capital:
            slots.class_ids.append(cid)
            rest = re.sub(rf"\b{n}\b", " CLASS ", rest, flags=re.IGNORECASE)

    def member(m: re.Match) -> str:
        digits = m.group(1) or m.group(2)
        bare = m.group(2) is not None
        if bare and (
            YEAR.match(digits)
            or NOT_MEMBER_BEFORE.search(m.string[: m.start()])
            or NOT_MEMBER_AFTER.match(m.string[m.end() :])
        ):
            return m.group(0)
        member_id = f"M{int(digits):04d}"
        if member_id not in slots.member_ids:
            slots.member_ids.append(member_id)
        return " MEMBER "

    rest = MEMBER.sub(member, rest)
    return slots, re.sub(r"\s+", " ", rest).strip()

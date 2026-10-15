from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class Channel(StrEnum):
    SMS = "sms"
    EMAIL = "email"
    CALL = "call"
    IN_PERSON = "in_person"


class Offer(BaseModel):
    offer_id: str
    name: str
    cost: float
    staff_minutes: int = 0
    inventory: int | None = None
    channels: list[Channel] = []


class MemberScore(BaseModel):
    member_id: str
    as_of: date
    segment: str
    churn_prob: float = Field(ge=0, le=1)
    monthly_value: float
    top_drivers: list[tuple[str, float]]
    features: dict[str, float]


class RuleFiring(BaseModel):
    rule_id: str
    description: str
    facts_matched: dict[str, object]
    effect: str


class CandidateAction(BaseModel):
    member_id: str
    offer_id: str
    channel: Channel
    uplift: float
    uplift_source: str
    cost: float
    staff_minutes: int
    rule_trace: list[RuleFiring] = []


class PlanItem(BaseModel):
    member_id: str
    offer_id: str
    channel: Channel
    expected_value: float
    explanation_id: str


class Explanation(BaseModel):
    explanation_id: str
    member_id: str
    churn_prob: float
    top_drivers: list[tuple[str, float]]
    rule_trace: list[RuleFiring]
    similar_cases: list[dict]
    graph_signals: list[str]
    summary: str


class PlanRequest(BaseModel):
    as_of: date
    budget: float
    staff_minutes: int
    max_contacts_per_member_per_30d: int = 1
    solver: str = "ga"


class Plan(BaseModel):
    request: PlanRequest
    items: list[PlanItem]
    total_cost: float
    total_staff_minutes: int
    expected_members_retained: float
    solver_stats: dict = {}

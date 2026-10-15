"""Response models for Stream A endpoints. Mirrored in frontend/src/api/types.ts."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from anchorai.schemas import MemberScore

RiskBand = Literal["high", "medium", "low"]


class MemberRow(BaseModel):
    member_id: str
    segment_id: int
    segment: str
    churn_prob: float
    risk_band: RiskBand
    monthly_value: float
    club_id: str
    lifetime: int
    contract_period: int
    age: int
    avg_class_frequency_total: float
    trend_ratio: float


class MemberPage(BaseModel):
    items: list[MemberRow]
    total: int
    page: int
    page_size: int


class MemberHit(BaseModel):
    member_id: str
    segment: str
    risk_band: RiskBand
    churn_prob: float


class SegmentCard(BaseModel):
    segment_id: int
    name: str
    description: str
    size: int
    churn_rate: float
    at_risk: int
    monthly_revenue: float
    profile: dict[str, float]


class AttendanceRow(BaseModel):
    class_id: str
    class_name: str
    instructor_id: str
    instructor_name: str
    visits_per_week: float


class InterventionRow(BaseModel):
    week_start: date
    offer_id: str | None
    channel: str | None
    treated: bool
    stayed: bool


class MemberDetail(BaseModel):
    score: MemberScore
    risk_band: RiskBand
    segment_id: int
    segment_description: str
    club_id: str
    profile: dict[str, float]
    segment_averages: dict[str, float]
    feature_labels: dict[str, str]
    attendance: list[AttendanceRow]
    interventions: list[InterventionRow]


class Kpis(BaseModel):
    total_members: int
    members_at_risk: int
    revenue_at_risk: float
    plan_coverage: float | None
    contacted: int
    reached: int
    retained: int
    outcome_week: date | None


class RiskBin(BaseModel):
    start: float
    end: float
    count: int


class SegmentMix(BaseModel):
    segment: str
    size: int
    at_risk: int


class OutcomeWeek(BaseModel):
    week_start: date
    contacted: int
    reached: int
    retained: int


class Dashboard(BaseModel):
    as_of: date
    kpis: Kpis
    risk_distribution: list[RiskBin]
    segment_mix: list[SegmentMix]
    outcome_trend: list[OutcomeWeek]

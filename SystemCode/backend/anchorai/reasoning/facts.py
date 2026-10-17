"""The facts rules can test, and how each member's facts are built from Stream A and the KG."""

import json
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from anchorai.catalog import DEFAULT_CONSTRAINTS, Constraints
from anchorai.features import FEATURES, LABELS
from anchorai.scenario.build import AS_OF

FactType = Literal["number", "bool", "category"]


@dataclass(frozen=True)
class FactSpec:
    type: FactType
    description: str
    source: str


KNOWN_FACTS: dict[str, FactSpec] = {
    **{f: FactSpec("number", LABELS.get(f, f), "features") for f in FEATURES},
    "churn_prob": FactSpec("number", "Calibrated churn probability (0-1)", "churn model"),
    "risk_band": FactSpec("category", "Risk band: low, medium or high", "churn model"),
    "segment": FactSpec("category", "Segment name", "segmentation"),
    "monthly_value": FactSpec("number", "Monthly membership value", "members"),
    "club_id": FactSpec("category", "Home club", "members"),
    "days_since_last_contact": FactSpec(
        "number", "Days since the last retention contact (absent if never)", "interventions"
    ),
    "contacts_last_30d": FactSpec(
        "number", "Retention contacts in the last 30 days", "interventions"
    ),
    "offers_last_90d": FactSpec("number", "Offers received in the last 90 days", "interventions"),
    "pt_last_90d": FactSpec("bool", "Had a free PT session in the last 90 days", "interventions"),
    "at_contact_cap": FactSpec(
        "bool", "Contacts in the last 30 days have reached the contact cap", "interventions"
    ),
    "at_offer_cap": FactSpec(
        "bool", "Offers in the last 90 days have reached the offer cap", "interventions"
    ),
    "lost_anchor_instructor": FactSpec(
        "bool", "An instructor who taught most of their classes has left", "knowledge graph"
    ),
    "anchor_instructor_share": FactSpec(
        "number", "Share of class visits with instructors who have left (0-1)", "knowledge graph"
    ),
    "class_cancelled": FactSpec("bool", "A class they attend was cancelled", "knowledge graph"),
    "cohort_risk": FactSpec(
        "number", "Mean churn probability of their class co-attendees", "knowledge graph"
    ),
}


def value_type(value: object) -> FactType:
    if isinstance(value, bool):
        return "bool"
    return "number" if isinstance(value, int | float) else "category"


SCORE_FACTS = ["churn_prob", "risk_band", "segment", "monthly_value", "club_id"]


def contact_facts(interventions: pd.DataFrame) -> pd.DataFrame:
    treated = interventions[interventions["treated"]]
    as_of = pd.Timestamp(AS_OF)
    by_member = treated.groupby("member_id")["week_start"]
    recent = treated[treated["week_start"] >= as_of - pd.Timedelta(days=90)]
    # Strict, so "contacted fewer than 30 days ago" and "a contact in the window" agree.
    last_30d = treated[treated["week_start"] > as_of - pd.Timedelta(days=30)]
    pt = recent[recent["offer_id"] == "free_pt_session"]
    return pd.DataFrame(
        {
            "days_since_last_contact": (as_of - by_member.max()).dt.days,
            "contacts_last_30d": last_30d.groupby("member_id").size(),
            "offers_last_90d": recent.groupby("member_id").size(),
            "pt_last_90d": pt.groupby("member_id").size() > 0,
        }
    )


def build_facts(
    scores: pd.DataFrame,
    features: pd.DataFrame,
    interventions: pd.DataFrame,
    kg: pd.DataFrame | None = None,
    caps: Constraints | None = None,
) -> dict[str, dict[str, Any]]:
    """Facts per member. `scores` and `features` are indexed by member_id.

    Missing facts are left out rather than defaulted, so rules on them simply don't match:
    never-contacted members have no `days_since_last_contact`, and without the KG there are
    no KG facts at all. `caps` sets the contact and offer limits behind `at_contact_cap` and
    `at_offer_cap`; it defaults to the catalogue defaults.
    """
    caps = caps or Constraints(**DEFAULT_CONSTRAINTS)
    frame = features[FEATURES].join(scores[SCORE_FACTS], how="inner")
    contacts = contact_facts(interventions).reindex(frame.index)
    for col in ("contacts_last_30d", "offers_last_90d"):
        contacts[col] = contacts[col].fillna(0)
    contacts["pt_last_90d"] = contacts["pt_last_90d"].fillna(False).astype(bool)
    contacts["at_contact_cap"] = (
        contacts["contacts_last_30d"] >= caps.max_contacts_per_member_per_30d
    )
    contacts["at_offer_cap"] = contacts["offers_last_90d"] >= caps.max_offers_per_member_per_90d
    frame = frame.join(contacts)
    if kg is not None:
        kg = kg.reindex(frame.index)
        for col in ("lost_anchor_instructor", "class_cancelled"):
            kg[col] = kg[col].fillna(False).astype(bool)
        frame = frame.join(kg)
    # Counts and 0/1 flags read better in traces as 1 than 1.0.
    for col in frame.select_dtypes("number").columns:
        values = frame[col].dropna()
        if frame[col].dtype != bool and (values == values.round()).all():
            frame[col] = frame[col].astype("Int64")
    # to_json gives plain Python types (no numpy scalars) and NaN -> None, which we drop.
    records = json.loads(frame.to_json(orient="index"))
    return {m: {k: v for k, v in r.items() if v is not None} for m, r in records.items()}

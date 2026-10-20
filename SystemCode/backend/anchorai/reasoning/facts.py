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
        "number",
        "Days since the last retention contact (absent if never)",
        "interventions + logged outcomes",
    ),
    "contacts_last_30d": FactSpec(
        "number", "Retention contacts in the last 30 days", "interventions + logged outcomes"
    ),
    "offers_last_90d": FactSpec(
        "number", "Offers received in the last 90 days", "interventions + logged outcomes"
    ),
    "pt_last_90d": FactSpec(
        "bool", "Had a free PT session in the last 90 days", "interventions + logged outcomes"
    ),
    "at_contact_cap": FactSpec(
        "bool",
        "Contacts in the last 30 days have reached the contact cap",
        "interventions + logged outcomes",
    ),
    "at_offer_cap": FactSpec(
        "bool",
        "Offers in the last 90 days have reached the offer cap",
        "interventions + logged outcomes",
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


FREE_PT = "free_pt_session"


def contact_facts(interventions: pd.DataFrame, logged: pd.DataFrame | None = None) -> pd.DataFrame:
    """Contact history from the intervention log plus contacts logged in the app.

    Every treated intervention is a contact and an offer. Every logged outcome is a contact, dated
    by `logged_at` (columns: member_id, week_start, offer_id, outcome); it is an offer unless
    the outcome is `no_answer`, and a free PT only if accepted. Days are counted from AS_OF, the
    scenario's "today", and contacts logged after it count as day 0.
    """
    treated = interventions[interventions["treated"]]
    history = pd.DataFrame(
        {
            "member_id": treated["member_id"],
            "week_start": treated["week_start"],
            "offered": True,
            "pt": treated["offer_id"] == FREE_PT,
        }
    )
    if logged is not None and len(logged):
        history = pd.concat(
            [
                history,
                pd.DataFrame(
                    {
                        "member_id": logged["member_id"],
                        "week_start": pd.to_datetime(logged["week_start"]),
                        "offered": logged["outcome"] != "no_answer",
                        "pt": (logged["offer_id"] == FREE_PT) & (logged["outcome"] == "accepted"),
                    }
                ),
            ],
            ignore_index=True,
        )
    as_of = pd.Timestamp(AS_OF)
    by_member = history.groupby("member_id")["week_start"]
    recent = history[history["week_start"] >= as_of - pd.Timedelta(days=90)]
    # Strict, so "contacted fewer than 30 days ago" and "a contact in the window" agree.
    last_30d = history[history["week_start"] > as_of - pd.Timedelta(days=30)]
    offers = recent[recent["offered"]]
    return pd.DataFrame(
        {
            "days_since_last_contact": (as_of - by_member.max()).dt.days.clip(lower=0),
            "contacts_last_30d": last_30d.groupby("member_id").size(),
            "offers_last_90d": offers.groupby("member_id").size(),
            "pt_last_90d": recent[recent["pt"]].groupby("member_id").size() > 0,
        }
    )


def build_facts(
    scores: pd.DataFrame,
    features: pd.DataFrame,
    interventions: pd.DataFrame,
    kg: pd.DataFrame | None = None,
    caps: Constraints | None = None,
    logged: pd.DataFrame | None = None,
) -> dict[str, dict[str, Any]]:
    """Facts per member. `scores` and `features` are indexed by member_id.

    Missing facts are left out rather than defaulted, so rules on them simply don't match:
    never-contacted members have no `days_since_last_contact`, and without the KG there are
    no KG facts at all. `caps` sets the contact and offer limits behind `at_contact_cap` and
    `at_offer_cap`; it defaults to the catalogue defaults. `logged` is the app's logged contacts.
    """
    caps = caps or Constraints(**DEFAULT_CONSTRAINTS)
    frame = features[FEATURES].join(scores[SCORE_FACTS], how="inner")
    contacts = contact_facts(interventions, logged).reindex(frame.index)
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

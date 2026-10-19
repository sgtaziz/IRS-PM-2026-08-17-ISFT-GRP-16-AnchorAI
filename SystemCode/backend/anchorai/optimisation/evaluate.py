"""Policy evaluator: grades a plan with the scenario's hidden truth. Never used to choose a plan."""

from dataclasses import dataclass

import pandas as pd

from anchorai.scenario.tables import read_tables


@dataclass(frozen=True)
class Truth:
    uplift: pd.Series  # (member_id, offer_id) -> true uplift of contacting the member now
    stay_if_left_alone: pd.Series  # member_id -> 1 - event_churn


def load_truth(tables: dict[str, pd.DataFrame] | None = None) -> Truth:
    tables = read_tables() if tables is None else tables
    uplift = tables["true_uplift"].set_index(["member_id", "offer_id"])["uplift"]
    churn = tables["true_churn"].set_index("member_id")["event_churn"]
    return Truth(uplift, 1 - churn)


def evaluate(plan: pd.DataFrame, truth: Truth) -> dict[str, float]:
    keys = pd.MultiIndex.from_frame(plan[["member_id", "offer_id"]])
    extra = float(truth.uplift.reindex(keys).fillna(0).sum())
    spend, minutes = float(plan["cost"].sum()), float(plan["staff_minutes"].sum())
    return {
        "contacts": len(plan),
        "spend": spend,
        "staff_minutes": minutes,
        "members_retained": float(truth.stay_if_left_alone.sum()) + extra,
        "extra_retained": extra,
        "estimated_extra": float(plan["est_uplift"].sum()),
        "per_1000_dollars": 1000 * extra / spend if spend else float("nan"),
        "per_staff_hour": 60 * extra / minutes if minutes else float("nan"),
    }

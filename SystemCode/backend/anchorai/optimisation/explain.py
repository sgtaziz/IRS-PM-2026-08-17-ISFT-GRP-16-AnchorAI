"""One Explanation per plan item: A's drivers, C's rules and graph signals, B's similar past cases."""

import json

import numpy as np
import pandas as pd

from anchorai.cbr.reasoner import CONTROL, CaseBase, estimate_uplift, nearest
from anchorai.features import LABELS
from anchorai.knowledge.signals import graph_signals
from anchorai.reasoning.models import RuleOutcome
from anchorai.schemas import Explanation

SIMILAR_CASES = 10
DRIVERS_IN_SUMMARY = 2


def similar_cases_for(
    case_base: CaseBase, chosen: pd.DataFrame, offer_names: dict[str, str]
) -> dict:
    """The nearest past cases for each (member, offer) in the plan, one neighbour search per offer."""
    out = {}
    for offer_id, rows in chosen.groupby("offer_id"):
        pool = case_base.cases[case_base.cases["arm"].isin([offer_id, CONTROL])]
        ids = rows["member_id"].to_numpy()
        dist, idx, keep = nearest(case_base, pool, ids, SIMILAR_CASES)
        name = offer_names.get(offer_id, offer_id)
        for k, member_id in enumerate(ids):
            cases = []
            for r, d in zip(pool.iloc[idx[k][keep[k]]].itertuples(), dist[k][keep[k]], strict=True):
                week = pd.Timestamp(r.week_start).date().isoformat()
                got = f"got {name}" if r.treated else "got no offer"
                cases.append(
                    {
                        "member_id": r.member_id,
                        "offer_id": r.offer_id if r.treated else None,
                        "week_start": week,
                        "stayed": bool(r.stayed),
                        "distance": round(float(d), 3),
                        "outcome": f"{r.member_id} {got} in the week of {week} and "
                        + ("stayed" if r.stayed else "left"),
                    }
                )
            out[member_id, offer_id] = cases
    return out


def _drivers(raw: str) -> list[tuple[str, float]]:
    return [(name, float(value)) for name, value in json.loads(raw)]


def _summary(row, drivers, firings, cases, offer_name: str) -> str:
    up = [LABELS.get(n, n).lower() for n, v in drivers if v > 0][:DRIVERS_IN_SUMMARY]
    risk = f"{row.risk_band.capitalize()} churn risk ({row.churn_prob:.0%})"
    risk += f", mainly {' and '.join(up)}." if up else "."
    rule = next((f for f in firings if f.rule_id == row.rule_id), None)
    why = f" {rule.description} ({row.rule_id.split('_')[0]})." if rule else ""
    treated = [c for c in cases if c["offer_id"]]
    control = [c for c in cases if not c["offer_id"]]
    seen = ""
    if treated and control:
        seen = (
            f" Of the {len(cases)} most similar past members, {sum(c['stayed'] for c in treated)} of "
            f"{len(treated)} who got {offer_name.lower()} stayed, against "
            f"{sum(c['stayed'] for c in control)} of {len(control)} with no offer."
        )
    points = round(100 * row.est_uplift)
    estimate = f" Estimated effect: {points:+d} point{'' if abs(points) == 1 else 's'} on the chance of staying."
    return risk + why + seen + estimate


def explain_plan(
    chosen: pd.DataFrame,
    explanation_ids: list[str],
    outcomes: dict[str, RuleOutcome],
    scores: pd.DataFrame,
    case_base: CaseBase,
    offer_names: dict[str, str],
) -> list[Explanation]:
    """Explanations for the chosen option rows, in order. `scores` is indexed by member_id."""
    similar = similar_cases_for(case_base, chosen, offer_names)
    out = []
    for row, explanation_id in zip(chosen.itertuples(), explanation_ids, strict=True):
        outcome = outcomes[row.member_id]
        drivers = _drivers(scores.at[row.member_id, "top_drivers"])
        cases = similar[row.member_id, row.offer_id]
        offer_name = offer_names.get(row.offer_id, row.offer_id)
        out.append(
            Explanation(
                explanation_id=explanation_id,
                member_id=row.member_id,
                churn_prob=float(np.round(row.churn_prob, 4)),
                top_drivers=drivers,
                rule_trace=outcome.firings,
                similar_cases=cases,
                graph_signals=graph_signals(outcome.facts),
                summary=_summary(row, drivers, outcome.firings, cases, offer_name),
            )
        )
    return out


def member_evidence(case_base: CaseBase, member_id: str, offer_names: dict[str, str]) -> list[dict]:
    """CBR's estimate for every offer for one member, with the past cases behind it, best estimate first."""
    # Shrinkage reads the spread across all members, so estimate everyone and keep this member.
    est = estimate_uplift(case_base)
    est = est[est["member_id"] == member_id]
    similar = similar_cases_for(case_base, est[["member_id", "offer_id"]], offer_names)
    rows = [
        {
            "offer_id": r.offer_id,
            "offer_name": offer_names.get(r.offer_id, r.offer_id),
            "estimate": round(float(r.uplift), 4),
            "local": None if pd.isna(r.local) else round(float(r.local), 4),
            "weight_on_local": round(float(r.weight), 3),
            "neighbours_treated": int(r.n_treated),
            "neighbours_control": int(r.n_control),
            "cases": similar[member_id, r.offer_id],
        }
        for r in est.itertuples()
    ]
    return sorted(rows, key=lambda r: -r["estimate"])

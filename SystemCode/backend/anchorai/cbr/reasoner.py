"""CBR offer reasoner (PLAN B4): kNN uplift over the intervention log, with similar cases as explanation.

A case is a member (problem), the offer they got or nothing (solution) and whether they stayed (outcome).
Settings and their evidence: notebooks/b_cbr.ipynb.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from anchorai.discovery.scores import load_features
from anchorai.scenario.tables import read_tables

K = 200
CONTROL = "control"
CASE_COLUMNS = ["member_id", "offer_id", "week_start", "treated", "stayed"]


@dataclass(frozen=True)
class CaseBase:
    cases: pd.DataFrame  # CASE_COLUMNS plus `arm` (offer_id, or "control")
    x: pd.DataFrame  # standardised member features, indexed by member_id

    @property
    def offers(self) -> list[str]:
        return sorted(self.cases.loc[self.cases["treated"], "offer_id"].unique())


def case_base_from(cases: pd.DataFrame, features: pd.DataFrame) -> CaseBase:
    x = (features - features.mean()) / features.std().replace(0, 1)
    randomised = cases.get("randomised", True)
    cases = cases[CASE_COLUMNS].reset_index(drop=True).assign(randomised=np.asarray(randomised))
    return CaseBase(cases.assign(arm=cases["offer_id"].fillna(CONTROL)), x)


def load_case_base() -> CaseBase:
    """The scenario's intervention log over Stream A's member features."""
    return case_base_from(read_tables()["interventions"], load_features())


def retain(case_base: CaseBase, new_cases: pd.DataFrame) -> CaseBase:
    """Add logged outcomes as cases, marked as not randomised.

    They serve as local precedents, but the offer averages that thin evidence shrinks toward come from
    randomised cases only: the planner contacts high-risk members on purpose, so logged stay rates are
    low for reasons that have nothing to do with the offer.
    """
    logged = new_cases[CASE_COLUMNS].assign(randomised=False)
    cases = pd.concat([case_base.cases[[*CASE_COLUMNS, "randomised"]], logged], ignore_index=True)
    return case_base_from(cases, case_base.x)


def nearest(case_base: CaseBase, pool: pd.DataFrame, query_ids: np.ndarray, k: int):
    """Distances, indices and a keep-mask of the k nearest pool cases, skipping the member's own cases."""
    case_ids = pool["member_id"].to_numpy()
    own = int(pool["member_id"].value_counts().reindex(query_ids).fillna(0).max())
    nn = NearestNeighbors(n_neighbors=min(k + own, len(pool)))
    dist, idx = nn.fit(case_base.x.loc[case_ids].to_numpy()).kneighbors(
        case_base.x.loc[query_ids].to_numpy()
    )
    not_self = case_ids[idx] != query_ids[:, None]
    return dist, idx, not_self & (np.cumsum(not_self, axis=1) <= k)


def _local(
    case_base: CaseBase, offer_id: str, query_ids: np.ndarray, k: int, kernel: bool
) -> pd.DataFrame:
    """Retrieve + reuse: treated minus control stay rate in one (distance-weighted) neighbourhood."""
    pool = case_base.cases[case_base.cases["arm"].isin([offer_id, CONTROL])]
    dist, idx, keep = nearest(case_base, pool, query_ids, k)
    # Gaussian kernel on the member's median neighbour distance: closer cases weigh more.
    scale = np.maximum(np.nanmedian(np.where(keep, dist, np.nan), axis=1, keepdims=True), 1e-9)
    w = (np.exp(-((dist / scale) ** 2)) if kernel else 1.0) * keep
    treated, stayed = pool["treated"].to_numpy()[idx], pool["stayed"].to_numpy(float)[idx]
    rates, noise, counts = [], 0.0, []
    for arm in (treated, ~treated):
        wa = w * arm
        with np.errstate(invalid="ignore", divide="ignore"):
            p = (wa * stayed).sum(1) / wa.sum(1)
            n_eff = wa.sum(1) ** 2 / (wa**2).sum(1)
        rates.append(p)
        noise = noise + p * (1 - p) / n_eff
        counts.append((keep & arm).sum(1))
    return pd.DataFrame(
        {
            "member_id": query_ids,
            "offer_id": offer_id,
            "local": rates[0] - rates[1],
            "noise": noise,
            "n_treated": counts[0],
            "n_control": counts[1],
        }
    )


def estimate_uplift(
    case_base: CaseBase, member_ids: np.ndarray | None = None, k: int = K, kernel: bool = True
) -> pd.DataFrame:
    """Uplift per (member, offer), shaped like `true_uplift`, plus the evidence behind each estimate.

    Revise is empirical-Bayes shrinkage toward the offer's average uplift: weight = spread between
    members / (spread + noise), i.e. (n·local + m·average) / (n + m) with n and m read from the data.
    """
    ids = case_base.x.index.to_numpy() if member_ids is None else np.asarray(member_ids)
    randomised = case_base.cases[case_base.cases["randomised"]]
    rate = randomised.groupby("arm")["stayed"].mean()
    frames = []
    for offer_id in case_base.offers:
        est = _local(case_base, offer_id, ids, k, kernel)
        est["prior"] = rate[offer_id] - rate[CONTROL]
        spread = max(est["local"].var() - est["noise"].mean(), 0.0)
        est["weight"] = (spread / (spread + est["noise"])).fillna(0.0)
        est["uplift"] = est["weight"] * est["local"].fillna(0) + (1 - est["weight"]) * est["prior"]
        frames.append(est)
    return pd.concat(frames, ignore_index=True)


def uplift_series(case_base: CaseBase) -> pd.Series:
    """CBR uplift indexed by (member_id, offer_id), the form the planner takes."""
    return estimate_uplift(case_base).set_index(["member_id", "offer_id"])["uplift"]


def similar_cases(case_base: CaseBase, member_id: str, offer_id: str, n: int = 10) -> list[dict]:
    """The nearest past cases behind one estimate, nearest first: precedents for the explanation."""
    pool = case_base.cases[case_base.cases["arm"].isin([offer_id, CONTROL])]
    dist, idx, keep = nearest(case_base, pool, np.array([member_id]), n)
    rows = pool.iloc[idx[0][keep[0]]]
    return [
        {
            "member_id": r.member_id,
            "offer_id": r.offer_id if r.treated else None,
            "week_start": pd.Timestamp(r.week_start).date().isoformat(),
            "stayed": bool(r.stayed),
            "distance": round(float(d), 3),
        }
        for r, d in zip(rows.itertuples(), dist[0][keep[0]], strict=True)
    ]

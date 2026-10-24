"""K-means behavioural segmentation (experiment E1)."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

SEGMENT_COLUMNS = [
    "lifetime",
    "avg_class_frequency_total",
    "trend_ratio",
    "contract_period",
    "avg_additional_charges_total",
    "age",
    "group_visits",
]
K_RANGE = range(2, 11)
K_CANDIDATES = range(3, 9)
# Silhouette is nearly flat across k on this data, so prefer the most detailed k that
# stays within this share of the best score.
SILHOUETTE_TOLERANCE = 0.05
STABILITY_SEEDS = 5


@dataclass
class Segmentation:
    labels: pd.Series
    profiles: pd.DataFrame
    card: dict
    scaler: StandardScaler
    kmeans: KMeans


def _matrix(features: pd.DataFrame) -> pd.DataFrame:
    x = features[SEGMENT_COLUMNS].copy()
    x["lifetime"] = np.log1p(x["lifetime"])
    return x


def choose_k(silhouettes: dict[int, float]) -> int:
    best = max(silhouettes[k] for k in K_CANDIDATES)
    return max(k for k in K_CANDIDATES if silhouettes[k] >= (1 - SILHOUETTE_TOLERANCE) * best)


def name_segment(p: pd.Series) -> str:
    if p["lifetime"] < 2:
        return "New and slipping" if p["trend_ratio"] < 0.8 else "New and settling in"
    if p["contract_period"] >= 9:
        return "Annual-contract loyalists"
    if p["avg_class_frequency_total"] < 1.3:
        return "Established but infrequent"
    return "Established class-goers" if p["group_visits"] >= 0.5 else "Established solo trainers"


def describe_segment(p: pd.Series) -> str:
    trend = (p["trend_ratio"] - 1) * 100
    direction = "down" if trend < 0 else "up"
    return (
        f"{p['lifetime']:.1f} months as members on {p['contract_period']:.1f}-month contracts, "
        f"{p['avg_class_frequency_total']:.1f} visits a week, {direction} {abs(trend):.0f}% "
        f"this month; {p['group_visits']:.0%} attend group classes."
    )


def fit_segments(
    features: pd.DataFrame, churn: pd.Series, train: pd.Series, seed: int
) -> Segmentation:
    """Fit on training members only, then assign every member; ids ordered by churn rate."""
    x = _matrix(features)
    scaler = StandardScaler().fit(x[train])
    z, z_train = scaler.transform(x), scaler.transform(x[train])

    silhouettes = {}
    for k in K_RANGE:
        fitted = KMeans(k, n_init=10, random_state=seed).fit(z_train)
        silhouettes[k] = float(silhouette_score(z_train, fitted.labels_))
    k = choose_k(silhouettes)
    kmeans = KMeans(k, n_init=10, random_state=seed).fit(z_train)
    raw = kmeans.predict(z)
    stability = [
        adjusted_rand_score(raw, KMeans(k, n_init=10, random_state=s).fit(z_train).predict(z))
        for s in range(seed + 1, seed + 1 + STABILITY_SEEDS)
    ]

    profile = features[SEGMENT_COLUMNS].assign(churn=churn.to_numpy(), raw=raw)
    order = profile.groupby("raw")["churn"].mean().sort_values(ascending=False).index
    remap = {old: new for new, old in enumerate(order)}
    labels = pd.Series([remap[r] for r in raw], index=features.index, name="segment_id")

    profiles = profile.assign(segment_id=labels.to_numpy()).groupby("segment_id").mean()
    profiles = profiles.drop(columns="raw").rename(columns={"churn": "churn_rate"})
    profiles["size"] = labels.value_counts().sort_index()
    profiles["name"] = profiles.apply(name_segment, axis=1)
    duplicated = profiles["name"].duplicated(keep=False)
    profiles.loc[duplicated, "name"] += " (" + profiles.index[duplicated].astype(str) + ")"
    profiles["description"] = profiles.apply(describe_segment, axis=1)
    profiles = profiles.reset_index()[
        ["segment_id", "name", "description", "size", "churn_rate", *SEGMENT_COLUMNS]
    ]

    card = {
        "k": k,
        "silhouette": silhouettes[k],
        "silhouette_by_k": {str(key): value for key, value in silhouettes.items()},
        "stability_ari": float(np.mean(stability)),
        "stability_ari_min": float(np.min(stability)),
        "fit_on": "train split",
        "columns": SEGMENT_COLUMNS,
    }
    return Segmentation(labels, profiles, card, scaler, kmeans)

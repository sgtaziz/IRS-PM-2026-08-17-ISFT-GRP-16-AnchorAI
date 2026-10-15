"""Stream A outputs on disk, and their loaders for the API and other streams."""

import json
from pathlib import Path

import pandas as pd

from anchorai.scenario.build import AS_OF
from anchorai.scenario.tables import generated_dir
from anchorai.schemas import MemberScore

TOP_DRIVERS = 5
# Calibrated probability cut-offs; shown as text labels, never colour alone.
RISK_BANDS = (("high", 0.6), ("medium", 0.3), ("low", 0.0))


def risk_band(p: float) -> str:
    return next(name for name, cutoff in RISK_BANDS if p >= cutoff)


def score_frame(
    members: pd.DataFrame,
    segment_ids: pd.Series,
    segment_names: pd.Series,
    probabilities: pd.Series,
    contributions: pd.DataFrame,
) -> pd.DataFrame:
    m = members.set_index("member_id")
    top = contributions.apply(
        lambda row: json.dumps(
            [
                [k, round(float(v), 4)]
                for k, v in row.reindex(row.abs().nlargest(TOP_DRIVERS).index).items()
            ]
        ),
        axis=1,
    )
    frame = pd.DataFrame(
        {
            "segment_id": segment_ids.astype("int64"),
            "segment": segment_ids.map(segment_names).astype("string"),
            "churn_prob": probabilities.astype("float64"),
            "risk_band": probabilities.map(risk_band).astype("string"),
            "monthly_value": m["monthly_value"],
            "club_id": m["club_id"],
            "top_drivers": top.astype("string"),
        },
        index=probabilities.index,
    )
    return frame.rename_axis("member_id").reset_index()


def load_scores(directory: Path | None = None) -> pd.DataFrame:
    return pd.read_parquet((directory or generated_dir()) / "member_scores.parquet")


def load_features(directory: Path | None = None) -> pd.DataFrame:
    return pd.read_parquet((directory or generated_dir()) / "features.parquet").set_index(
        "member_id"
    )


def to_member_score(row: pd.Series, features: pd.Series) -> MemberScore:
    return MemberScore(
        member_id=row["member_id"],
        as_of=AS_OF,
        segment=row["segment"],
        churn_prob=row["churn_prob"],
        monthly_value=row["monthly_value"],
        top_drivers=[tuple(d) for d in json.loads(row["top_drivers"])],
        features={k: float(v) for k, v in features.items()},
    )


def load_member_scores(directory: Path | None = None) -> list[MemberScore]:
    """Every member's `MemberScore` (the A -> B, C contract)."""
    scores, features = load_scores(directory), load_features(directory)
    return [to_member_score(row, features.loc[row["member_id"]]) for _, row in scores.iterrows()]


def load_model_card(directory: Path | None = None) -> dict:
    return json.loads(((directory or generated_dir()) / "model_card.json").read_text())

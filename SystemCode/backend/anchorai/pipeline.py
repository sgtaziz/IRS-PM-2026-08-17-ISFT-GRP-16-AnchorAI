"""`anchorai data build`: raw Kaggle CSV -> data tables, segments, churn scores, uplift."""

import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from anchorai.config import get_settings
from anchorai.discovery import churn, segments
from anchorai.discovery.scores import score_frame
from anchorai.discovery.uplift import t_learner
from anchorai.features import build_features
from anchorai.scenario.build import build_tables, find_raw_csv, load_kaggle
from anchorai.scenario.tables import write_tables


def run(seed: int | None = None, out: Path | None = None) -> Path:
    settings = get_settings()
    seed = settings.anchorai_seed if seed is None else seed
    out = out or settings.anchorai_data_dir / "generated"
    raw = load_kaggle(find_raw_csv(settings.anchorai_data_dir / "raw"))

    tables = build_tables(raw, seed)
    write_tables(tables, out)
    members = tables["members"]
    labels = members.set_index("member_id")
    features = build_features(members)
    is_train = labels["split"] == "train"

    seg = segments.fit_segments(features, labels["churn"], is_train, seed)
    result = churn.train(features, labels["churn"], labels["split"], seed)
    uplift = t_learner(features, tables["interventions"], list(tables["offers"]["offer_id"]), seed)

    names = seg.profiles.set_index("segment_id")["name"]
    scores = score_frame(members, seg.labels, names, result.probabilities, result.contributions)
    features.rename_axis("member_id").reset_index().to_parquet(
        out / "features.parquet", index=False
    )
    seg.profiles.to_parquet(out / "segments.parquet", index=False)
    scores.to_parquet(out / "member_scores.parquet", index=False)
    uplift.to_parquet(out / "uplift_tlearner.parquet", index=False)

    card = {
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": seed,
        "source": raw_name(settings.anchorai_data_dir / "raw"),
        "n_members": len(members),
        "segmentation": seg.card,
        "churn": result.card,
        "uplift": {"method": "T-learner, mean(LR, LightGBM) per arm"},
    }
    (out / "model_card.json").write_text(json.dumps(card, indent=2, default=_json_default))
    models = out / "models"
    models.mkdir(exist_ok=True)
    joblib.dump({"scaler": seg.scaler, "kmeans": seg.kmeans}, models / "segments.joblib")
    joblib.dump(result.model, models / "churn.joblib")
    return out


def raw_name(raw_dir: Path) -> str:
    return find_raw_csv(raw_dir).name


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    raise TypeError(type(value))

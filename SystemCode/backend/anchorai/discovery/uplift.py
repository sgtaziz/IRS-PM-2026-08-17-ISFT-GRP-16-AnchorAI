"""T-learner uplift baseline (PLAN.md A6, input to experiment E3).

One outcome model per arm (each offer, plus untreated controls); uplift is the difference
in predicted stay probability. Each arm model is a mean of LR and a small LightGBM.
"""

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from anchorai.features import FEATURES


def _arm_model(x: np.ndarray, y: np.ndarray, seed: int):
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(x, y)
    gbm = LGBMClassifier(
        n_estimators=150,
        learning_rate=0.03,
        num_leaves=7,
        min_child_samples=30,
        random_state=seed,
        n_jobs=1,
        deterministic=True,
        verbose=-1,
    ).fit(x, y)
    return lambda z: (lr.predict_proba(z)[:, 1] + gbm.predict_proba(z)[:, 1]) / 2


def t_learner(
    features: pd.DataFrame, interventions: pd.DataFrame, offer_ids: list[str], seed: int
) -> pd.DataFrame:
    """Estimated uplift for every (member, offer), long format like `true_uplift`."""
    x_all = features[FEATURES].to_numpy()
    rows = features.loc[interventions["member_id"], FEATURES].to_numpy()
    stayed = interventions["stayed"].to_numpy().astype(int)
    control = ~interventions["treated"].to_numpy()
    p_control = _arm_model(rows[control], stayed[control], seed)(x_all)
    frames = []
    for offer_id in offer_ids:
        arm = (interventions["offer_id"] == offer_id).fillna(False).to_numpy()
        p_treated = _arm_model(rows[arm], stayed[arm], seed)(x_all)
        frames.append(
            pd.DataFrame(
                {"member_id": features.index, "offer_id": offer_id, "uplift": p_treated - p_control}
            )
        )
    return pd.concat(frames).sort_values(["member_id", "offer_id"], ignore_index=True)

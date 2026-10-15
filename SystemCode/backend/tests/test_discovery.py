from pathlib import Path

import numpy as np
import pandas as pd

from anchorai.discovery import churn
from anchorai.features import build_features
from anchorai.scenario.tables import read_tables

FIXTURES = Path(__file__).parent / "fixtures"


def _members(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    m = read_tables(FIXTURES)["members"].sample(n, replace=True, random_state=0)
    m = m.reset_index(drop=True)
    m["member_id"] = [f"M{i:04d}" for i in range(n)]
    for col in ("avg_additional_charges_total", "avg_class_frequency_total", "age"):
        m[col] = (m[col] * rng.uniform(0.8, 1.2, n)).round(2)
    m["avg_class_frequency_current_month"] *= rng.uniform(0.7, 1.3, n)
    m["age"] = m["age"].round().astype("int64")
    m["split"] = np.where(rng.random(n) < 0.25, "test", "train")
    return m


def test_test_labels_never_reach_the_churn_model():
    m = _members()
    features = build_features(m)
    labels = m.set_index("member_id")
    shuffled = labels["churn"].copy()
    test = labels["split"] == "test"
    shuffled[test] = 1 - shuffled[test]

    a = churn.train(features, labels["churn"], labels["split"], seed=1)
    b = churn.train(features, shuffled, labels["split"], seed=1)
    np.testing.assert_array_equal(a.probabilities.to_numpy(), b.probabilities.to_numpy())
    assert a.card["test"]["f1"] != b.card["test"]["f1"]

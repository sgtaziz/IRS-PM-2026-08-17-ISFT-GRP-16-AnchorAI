from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from anchorai.features import build_features
from anchorai.scenario.build import (
    EVENT_EFFECTS,
    build_tables,
    build_true_churn,
    event_exposure,
)
from anchorai.scenario.tables import KAGGLE_COLUMNS, read_tables

FIXTURES = Path(__file__).parent / "fixtures"


def test_exposure_is_the_share_of_visits_hit():
    t = read_tables(FIXTURES)
    exposure = event_exposure(t["attendance"], t["classes"], t["events"])
    # M0006 splits 1.50 + 1.00 visits between I01 (left) and I02; M0002 only trains with I01.
    assert exposure.loc["M0006", "lost_instructor_share"] == pytest.approx(0.6)
    assert exposure.loc["M0002", "lost_instructor_share"] == pytest.approx(1.0)
    assert exposure.loc["M0004", "cancelled_share"] == pytest.approx(1.0)
    assert exposure.loc["M0001"].tolist() == [0.0, 0.0]
    assert "M0003" not in exposure.index


def test_only_exposed_members_get_riskier():
    t = read_tables(FIXTURES)
    features = build_features(t["members"])
    exposure = event_exposure(t["attendance"], t["classes"], t["events"])
    truth = build_true_churn(features, exposure, np.random.default_rng(0), EVENT_EFFECTS)
    exposed = (truth["lost_instructor_share"] > 0) | (truth["cancelled_share"] > 0)
    assert exposed.any() and (~exposed).any()
    assert (truth.loc[~exposed, "event_churn"] == truth.loc[~exposed, "base_churn"]).all()
    assert (truth.loc[exposed, "event_churn"] > truth.loc[exposed, "base_churn"]).all()


def test_events_only_change_outcomes_from_their_week():
    members = read_tables(FIXTURES)["members"][list(KAGGLE_COLUMNS)]
    raw = members.sample(600, replace=True, random_state=0).reset_index(drop=True)
    off = build_tables(raw, seed=3, event_effects={k: 0.0 for k in EVENT_EFFECTS})
    # An effect this large makes exposed, uncontacted members certain to leave.
    on = build_tables(raw, seed=3, event_effects={k: 50.0 for k in EVENT_EFFECTS})

    a, b = on["interventions"], off["interventions"]
    assert a["member_id"].tolist() == b["member_id"].tolist()
    event_week = on["events"]["week_start"].min()
    before = (a["week_start"] < event_week).to_numpy()
    assert before.any()
    assert (a.loc[before, "stayed"].to_numpy() == b.loc[before, "stayed"].to_numpy()).all()

    truth = on["true_churn"].set_index("member_id")
    hit = truth.index[(truth["lost_instructor_share"] > 0) | (truth["cancelled_share"] > 0)]
    after = a[(a["week_start"] >= event_week) & ~a["treated"] & a["member_id"].isin(hit)]
    assert len(after) > 0
    assert not after["stayed"].any()
    assert (off["true_churn"]["event_churn"] == off["true_churn"]["base_churn"]).all()
    assert (on["true_uplift"]["uplift"] != off["true_uplift"]["uplift"]).any()
    assert (
        on["true_uplift"]
        .set_index("member_id")
        .drop(index=hit)
        .equals(off["true_uplift"].set_index("member_id").drop(index=hit))
    )
    pd.testing.assert_frame_equal(on["members"], off["members"], check_like=False)

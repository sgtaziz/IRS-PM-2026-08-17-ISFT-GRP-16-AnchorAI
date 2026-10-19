import numpy as np
import pandas as pd
import pytest

from anchorai.cbr.reasoner import case_base_from, estimate_uplift, retain, similar_cases

OFFERS = ["checkin_message", "free_pt_session"]


@pytest.fixture
def case_base():
    rng = np.random.default_rng(0)
    ids = [f"M{i:04d}" for i in range(80)]
    features = pd.DataFrame(rng.normal(size=(80, 3)), index=ids, columns=["a", "b", "c"])
    arm = rng.choice([None, *OFFERS], size=60)
    cases = pd.DataFrame(
        {
            "member_id": ids[:60],
            "offer_id": arm,
            "week_start": pd.Timestamp("2026-08-03"),
            "treated": [a is not None for a in arm],
            "stayed": rng.random(60) < 0.7,
        }
    )
    return case_base_from(cases, features)


def test_a_member_never_retrieves_their_own_case(case_base):
    member = case_base.cases.loc[case_base.cases["treated"], "member_id"].iloc[0]
    offer = case_base.cases.set_index("member_id").loc[member, "offer_id"]
    precedents = similar_cases(case_base, member, offer, n=10)
    assert len(precedents) == 10
    assert member not in {p["member_id"] for p in precedents}

    # Logged outcomes can add more cases for the same member; they are skipped too.
    again = case_base.cases[case_base.cases["member_id"] == member]
    grown = retain(case_base, pd.concat([again, again]))
    assert member not in {p["member_id"] for p in similar_cases(grown, member, offer, n=10)}


def test_estimates_cover_every_member_and_offer_and_fall_back_without_signal(case_base):
    est = estimate_uplift(case_base, k=20)
    assert len(est) == len(case_base.x) * len(OFFERS)
    assert est["uplift"].notna().all()

    # Everyone stayed: there is nothing to learn, so every estimate is the offer's average (zero).
    flat = case_base_from(case_base.cases.assign(stayed=True), case_base.x)
    assert estimate_uplift(flat, k=20)["uplift"].abs().max() == pytest.approx(0)

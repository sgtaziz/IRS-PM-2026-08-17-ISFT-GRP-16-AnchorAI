import pandas as pd
import pytest

from anchorai.optimisation.baselines import POLICIES
from anchorai.optimisation.evaluate import Truth, evaluate
from anchorai.optimisation.model import Limits, violations


@pytest.fixture
def options():
    rows = [
        ("M1", "free_pt_session", 40.0, 60, "trainer", 0, 0.9, 0.30),
        ("M1", "checkin_message", 0.0, 5, "", 1, 0.9, 0.05),
        ("M2", "free_pt_session", 40.0, 60, "trainer", 0, 0.8, 0.25),
        ("M3", "class_pass", 15.0, 10, "", 0, 0.7, 0.10),
        ("M4", "discount_1m", 12.0, 15, "", 0, 0.6, 0.08),
        ("M4", "checkin_message", 0.0, 5, "", 1, 0.6, 0.02),
        ("M5", "checkin_message", 0.0, 5, "", 0, 0.5, 0.03),
    ]
    cols = ["member_id", "offer_id", "cost", "staff_minutes", "required_skill", "rank"]
    frame = pd.DataFrame(rows, columns=[*cols, "churn_prob", "est_uplift"])
    frame["monthly_value"] = 72.0
    frame["value"] = frame["est_uplift"] * frame["monthly_value"] * 6 - frame["cost"]
    return frame


TIGHT = Limits(budget=50, staff_minutes=80, trainer_minutes=60, stock={"free_pt_session": 1})
# One case per limit, each the only tight one, so dropping any check from `fill` breaks a plan.
LOOSE = {"budget": 1000.0, "staff_minutes": 1000, "trainer_minutes": 1000}
BINDING = {
    "budget": Limits(**{**LOOSE, "budget": 45}),
    "staff minutes": Limits(**{**LOOSE, "staff_minutes": 70}),
    "trainer minutes": Limits(**{**LOOSE, "trainer_minutes": 60}),
    "stock": Limits(**LOOSE, stock={"free_pt_session": 1}),
}


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("limit", BINDING)
def test_baseline_plans_are_feasible(options, policy, limit):
    plan = POLICIES[policy](options, BINDING[limit], 0)
    assert len(plan) > 0
    assert violations(plan, options, BINDING[limit]) == {}


def test_violations_name_every_broken_limit(options):
    plan = options.loc[[0, 1, 2]]  # M1 twice, two PT sessions
    assert set(violations(plan, options, TIGHT)) == {
        "members contacted twice",
        "budget ($)",
        "staff minutes",
        "trainer minutes",
        "free_pt_session stock",
    }


def test_evaluator_adds_true_uplift_to_the_no_contact_baseline(options):
    truth = Truth(
        uplift=pd.Series(
            [0.2, 0.1, -0.05],
            index=pd.MultiIndex.from_tuples(
                [("M1", "free_pt_session"), ("M3", "class_pass"), ("M4", "discount_1m")]
            ),
        ),
        stay_if_left_alone=pd.Series(
            [0.5, 0.6, 0.7, 0.8, 0.9], index=["M1", "M2", "M3", "M4", "M5"]
        ),
    )
    result = evaluate(options.loc[[0, 3, 4]], truth)
    assert result["extra_retained"] == pytest.approx(0.25)
    assert result["members_retained"] == pytest.approx(3.5 + 0.25)
    assert result["spend"] == 67.0

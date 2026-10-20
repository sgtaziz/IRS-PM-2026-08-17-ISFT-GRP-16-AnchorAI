"""The weekly planning problem: options, limits, the planner's objective and the feasibility check.

A plan is a subset of rows of the options table, at most one per member. "No contact" has no row.
"""

from dataclasses import dataclass, field

import pandas as pd
from sqlmodel import Session

from anchorai import catalog
from anchorai.catalog import Constraints, OfferIn, StaffRow
from anchorai.cbr.reasoner import load_case_base, uplift_series
from anchorai.discovery.scores import load_scores
from anchorai.reasoning.engine import run_many
from anchorai.reasoning.models import RuleOutcome
from anchorai.reasoning.service import active_rules, all_facts, drop_inactive
from anchorai.scenario.tables import generated_dir

# Months of fees a retained member is worth to the planner (decision #2).
HORIZON_MONTHS = 6
TRAINER = "trainer"
OPTION_COLUMNS = ["member_id", "offer_id", "channel", "rule_id", "rank"]


@dataclass(frozen=True)
class Limits:
    budget: float
    staff_minutes: int
    trainer_minutes: int
    stock: dict[str, int] = field(default_factory=dict)


@dataclass
class Instance:
    options: pd.DataFrame
    offers: list[OfferIn]
    staff: list[StaffRow]
    constraints: Constraints
    outcomes: dict[str, RuleOutcome]

    def limits(self, budget: float | None = None, staff_minutes: int | None = None) -> Limits:
        """The week's limits; budget and staff minutes default to the catalogue settings."""
        return limits_for(
            self.constraints.default_budget if budget is None else budget,
            self.constraints.default_staff_minutes if staff_minutes is None else staff_minutes,
            self.offers,
            self.staff,
        )


def limits_for(
    budget: float, staff_minutes: int, offers: list[OfferIn], staff: list[StaffRow]
) -> Limits:
    trainer = int(60 * sum(s.weekly_hours for s in staff if TRAINER in s.skills))
    stock = {o.offer_id: o.inventory for o in offers if o.inventory is not None}
    return Limits(budget, staff_minutes, trainer, stock)


def build_options(
    outcomes: dict[str, RuleOutcome],
    offers: list[OfferIn],
    scores: pd.DataFrame,
    uplift: pd.Series,
    horizon: int = HORIZON_MONTHS,
) -> pd.DataFrame:
    """One row per allowed (member, offer, channel); rank 0 is the playbook's top offer.

    `scores` is indexed by member_id; `uplift` by (member_id, offer_id).
    """
    # Rules can still propose an offer an admin deleted from the catalogue; it is not available.
    available = {o.offer_id for o in offers}
    rows = [
        (m, p.offer_id, p.channel, p.rule_id, rank)
        for m, outcome in outcomes.items()
        for rank, p in enumerate(p for p in outcome.allowed if p.offer_id in available)
    ]
    options = pd.DataFrame(rows, columns=OPTION_COLUMNS)
    catalogue = pd.DataFrame([o.model_dump() for o in offers]).set_index("offer_id")
    options = options.join(catalogue[["cost", "staff_minutes", "required_skill"]], on="offer_id")
    options = options.join(scores[["churn_prob", "risk_band", "monthly_value"]], on="member_id")
    keys = pd.MultiIndex.from_frame(options[["member_id", "offer_id"]])
    options["est_uplift"] = uplift.reindex(keys).to_numpy()
    options["value"] = options["est_uplift"] * options["monthly_value"] * horizon - options["cost"]
    return options


def load_tlearner_uplift() -> pd.Series:
    """Stream A's T-learner uplift, indexed by (member_id, offer_id)."""
    frame = pd.read_parquet(generated_dir() / "uplift_tlearner.parquet")
    return frame.set_index(["member_id", "offer_id"])["uplift"]


def load_instance(session: Session, uplift: pd.Series | None = None) -> Instance:
    """This week's problem from the live catalogue, rule base and scores; CBR uplift by default."""
    offers = catalog.list_offers(session, active_only=True)
    _, rules = active_rules(session)
    outcomes = {
        m: drop_inactive(session, o) for m, o in run_many(rules, all_facts(session)).items()
    }
    scores = load_scores().set_index("member_id")
    options = build_options(
        outcomes, offers, scores, uplift_series(load_case_base()) if uplift is None else uplift
    )
    return Instance(
        options, offers, catalog.list_staff(session), catalog.get_constraints(session), outcomes
    )


def plan_value(plan: pd.DataFrame) -> float:
    """What the planner believes a plan is worth in dollars: Σ est_uplift × fee × horizon − cost."""
    return float(plan["value"].sum())


def violations(plan: pd.DataFrame, options: pd.DataFrame, limits: Limits) -> dict[str, float]:
    """Every broken limit and by how much; an empty dict means the plan is feasible."""
    trainer = plan["required_skill"] == TRAINER
    over = {
        "not an allowed option": (~plan.index.isin(options.index)).sum(),
        "members contacted twice": plan["member_id"].duplicated().sum(),
        "budget ($)": plan["cost"].sum() - limits.budget,
        "staff minutes": plan["staff_minutes"].sum() - limits.staff_minutes,
        "trainer minutes": plan.loc[trainer, "staff_minutes"].sum() - limits.trainer_minutes,
    }
    used = plan["offer_id"].value_counts()
    for offer_id, stock in limits.stock.items():
        over[f"{offer_id} stock"] = used.get(offer_id, 0) - stock
    return {k: float(v) for k, v in over.items() if v > 0}

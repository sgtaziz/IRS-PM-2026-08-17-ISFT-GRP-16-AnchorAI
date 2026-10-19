"""Baseline policies for E4. All share `fill`, so they differ only in the order they consider options."""

from collections.abc import Callable

import pandas as pd

from anchorai.config import get_settings
from anchorai.optimisation.model import TRAINER, Limits

Policy = Callable[[pd.DataFrame, Limits, int | None], pd.DataFrame]


def fill(ordered: pd.DataFrame, limits: Limits) -> pd.DataFrame:
    """Walk the options in order and take each one that still fits every limit (first fit)."""
    stock = dict(limits.stock)
    spent = used = trainer = 0.0
    taken, keep = set(), []
    for i, r in zip(ordered.index, ordered.itertuples(), strict=True):
        is_trainer = r.required_skill == TRAINER
        if (
            r.member_id in taken
            or spent + r.cost > limits.budget
            or used + r.staff_minutes > limits.staff_minutes
            or (is_trainer and trainer + r.staff_minutes > limits.trainer_minutes)
            or stock.get(r.offer_id, 1) < 1
        ):
            continue
        taken.add(r.member_id)
        spent += r.cost
        used += r.staff_minutes
        trainer += r.staff_minutes if is_trainer else 0
        if r.offer_id in stock:
            stock[r.offer_id] -= 1
        keep.append(i)
    return ordered.loc[keep]


def _top(options: pd.DataFrame) -> pd.DataFrame:
    return options[options["rank"] == 0]


def contact_all(options: pd.DataFrame, limits: Limits, seed: int | None = None) -> pd.DataFrame:
    """Playbook top offer, members in random order."""
    seed = get_settings().anchorai_seed if seed is None else seed
    return fill(_top(options).sample(frac=1, random_state=seed), limits)


def risk_top_k(options: pd.DataFrame, limits: Limits, seed: int | None = None) -> pd.DataFrame:
    """Playbook top offer, highest churn risk first."""
    ordered = _top(options).sort_values(["churn_prob", "member_id"], ascending=[False, True])
    return fill(ordered, limits)


def greedy_uplift(options: pd.DataFrame, limits: Limits, seed: int | None = None) -> pd.DataFrame:
    """Any option worth more than it costs, best value per share of budget and staff time first."""
    worth = options[options["value"] > 0]
    share = worth["cost"] / max(limits.budget, 1e-9) + worth["staff_minutes"] / max(
        limits.staff_minutes, 1
    )
    ordered = worth.assign(density=worth["value"] / share).sort_values(
        ["density", "member_id"], ascending=[False, True]
    )
    return fill(ordered, limits).drop(columns="density")


POLICIES: dict[str, Policy] = {
    "contact-all": contact_all,
    "risk-top-k": risk_top_k,
    "greedy-uplift": greedy_uplift,
}

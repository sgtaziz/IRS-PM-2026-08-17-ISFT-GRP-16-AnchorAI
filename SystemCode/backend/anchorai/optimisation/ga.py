"""Genetic-algorithm planner (PLAN B2) on the full objective: spillover and diminishing returns.

A chromosome has one gene per member with an allowed option; gene k picks that member's k-th option, 0 = no contact.
Settings and their evidence: notebooks/b_ga.ipynb.
"""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from deap import base, creator, tools

from anchorai.config import get_settings
from anchorai.optimisation.baselines import greedy_uplift
from anchorai.optimisation.model import HORIZON_MONTHS, TRAINER, Limits
from anchorai.scenario.tables import read_tables

# Spillover strength and diminishing-returns rate (decision #5; sensitivity in E5).
BETA, DECAY = 0.5, 0.02


def load_cohorts() -> pd.DataFrame:
    """Class cohort rows (HANDOFFS #7): member, class, share of their own class visits, instructor.

    Built from Stream A's attendance table until C's KG function lands (HANDOFFS #34).
    """
    tables = read_tables()
    att = tables["attendance"]
    share = att["visits_per_week"] / att.groupby("member_id")["visits_per_week"].transform("sum")
    rows = att.assign(weight=share).merge(
        tables["classes"][["class_id", "instructor_id"]], on="class_id"
    )
    return rows[["member_id", "class_id", "weight", "instructor_id"]]


@dataclass
class Problem:
    """The options table as arrays, one gene per member with an option."""

    slot_options: list[np.ndarray]  # per gene: the option positions it can pick
    cost: np.ndarray
    minutes: np.ndarray
    trainer: np.ndarray
    offer: np.ndarray  # offer index per option, for stock
    gross: np.ndarray  # est_uplift x fee x horizon per option, dollars before cost
    slot_of: np.ndarray  # gene of each option
    share: np.ndarray  # genes x classes: class weight / (class size - 1)
    member_class: np.ndarray  # genes x classes: 1 if the member attends
    group: np.ndarray  # main instructor per gene, -1 for members in no class
    stock: np.ndarray  # per offer index; inf = unlimited


def build_problem(options: pd.DataFrame, cohorts: pd.DataFrame, limits: Limits) -> Problem:
    members = options["member_id"].unique()
    slot_of = pd.Series(np.arange(len(members)), index=members).loc[options["member_id"]].to_numpy()
    offer_ids = sorted(options["offer_id"].unique())
    classes = sorted(cohorts["class_id"].unique())
    size = cohorts.groupby("class_id")["member_id"].nunique().reindex(classes).to_numpy()
    mine = cohorts[cohorts["member_id"].isin(members)]
    weight = mine.pivot_table(
        index="member_id", columns="class_id", values="weight", fill_value=0.0
    ).reindex(index=members, columns=classes, fill_value=0.0)
    main = (
        mine.sort_values("weight", ascending=False)
        .drop_duplicates("member_id")
        .set_index("member_id")["instructor_id"]
    )
    instructor = {i: n for n, i in enumerate(sorted(cohorts["instructor_id"].unique()))}
    return Problem(
        slot_options=[np.flatnonzero(slot_of == s) for s in range(len(members))],
        cost=options["cost"].to_numpy(float),
        minutes=options["staff_minutes"].to_numpy(float),
        trainer=(options["required_skill"] == TRAINER).to_numpy(),
        offer=options["offer_id"].map({o: i for i, o in enumerate(offer_ids)}).to_numpy(),
        gross=(options["est_uplift"] * options["monthly_value"] * HORIZON_MONTHS).to_numpy(float),
        slot_of=slot_of,
        share=weight.to_numpy() / np.maximum(size - 1, 1),
        member_class=(weight.to_numpy() > 0).astype(float),
        group=main.reindex(members).map(instructor).fillna(-1).astype(int).to_numpy(),
        stock=np.array([limits.stock.get(o, np.inf) for o in offer_ids], float),
    )


def chosen(problem: Problem, genes: np.ndarray) -> np.ndarray:
    """Option positions picked by a chromosome."""
    return np.array(
        [problem.slot_options[s][genes[s] - 1] for s in np.flatnonzero(genes)], dtype=int
    )


def encode(problem: Problem, picks) -> np.ndarray:
    """The chromosome for a set of option positions, e.g. a baseline plan."""
    genes = np.zeros(len(problem.slot_options), int)
    for o in picks:
        s = problem.slot_of[o]
        genes[s] = int(np.flatnonzero(problem.slot_options[s] == o)[0]) + 1
    return genes


def objective(
    problem: Problem, picks: np.ndarray, beta: float = BETA, decay: float = DECAY
) -> float:
    """Spillover-boosted value with diminishing returns per instructor, minus cost, in dollars."""
    if len(picks) == 0:
        return 0.0
    slots = problem.slot_of[picks]
    in_plan = np.zeros(len(problem.slot_options))
    in_plan[slots] = 1.0
    # Weighted share of each contacted member's classmates who are also contacted (themselves excluded).
    counts = in_plan @ problem.member_class
    own = (problem.share[slots] * problem.member_class[slots]).sum(1)
    gross = problem.gross[picks] * (1 + beta * (problem.share[slots] @ counts - own))
    damp = np.ones(len(picks))
    grouped = problem.group[slots] >= 0
    if decay and grouped.any():
        # Within each instructor's members the n-th most valuable contact counts 1 / (1 + decay·(n − 1)).
        g, v = problem.group[slots][grouped], gross[grouped]
        order = np.lexsort((-v, g))
        first = np.r_[0, np.flatnonzero(np.diff(g[order])) + 1]
        rank = np.arange(len(order)) - np.repeat(first, np.diff(np.r_[first, len(order)]))
        d = np.empty(len(order))
        d[order] = 1 / (1 + decay * rank)
        damp[grouped] = d
    return float((gross * damp).sum() - problem.cost[picks].sum())


def repair(problem: Problem, genes: np.ndarray, limits: Limits) -> np.ndarray:
    """Drop the lowest value-per-resource picks until every limit holds."""
    picks = chosen(problem, genes)
    if len(picks) == 0:
        return genes
    density = (problem.gross[picks] - problem.cost[picks]) / (
        problem.cost[picks] / max(limits.budget, 1e-9)
        + problem.minutes[picks] / max(limits.staff_minutes, 1)
    )
    p = picks[np.argsort(-density, kind="stable")]
    keep = np.ones(len(p), bool)
    onehot = np.eye(len(problem.stock))[problem.offer[p]]
    for _ in range(3):  # dropping items changes the running totals, so re-check a few times
        k = keep.astype(float)
        stock_used = np.cumsum(onehot * k[:, None], axis=0)[np.arange(len(p)), problem.offer[p]]
        keep &= (
            (np.cumsum(problem.cost[p] * k) <= limits.budget + 1e-9)
            & (np.cumsum(problem.minutes[p] * k) <= limits.staff_minutes)
            & (np.cumsum(problem.minutes[p] * problem.trainer[p] * k) <= limits.trainer_minutes)
            & (stock_used <= problem.stock[problem.offer[p]])
        )
    out = genes.copy()
    out[problem.slot_of[p[~keep]]] = 0
    return out


def penalty(problem: Problem, genes: np.ndarray, limits: Limits) -> float:
    """Dollars per unit over any limit; used only when repair is switched off."""
    p = chosen(problem, genes)
    over = max(problem.cost[p].sum() - limits.budget, 0)
    over += max(problem.minutes[p].sum() - limits.staff_minutes, 0)
    over += max((problem.minutes[p] * problem.trainer[p]).sum() - limits.trainer_minutes, 0)
    over += np.maximum(
        np.bincount(problem.offer[p], minlength=len(problem.stock)) - problem.stock, 0
    ).sum()
    return 1000.0 * float(over)


def run_ga(
    problem: Problem,
    limits: Limits,
    seed_genes: np.ndarray,
    beta: float = BETA,
    decay: float = DECAY,
    pop_size: int = 100,
    generations: int = 300,
    cx_prob: float = 0.7,
    mutations_per_child: float = 2.0,
    tournament: int = 3,
    elite: int = 2,
    use_repair: bool = True,
    seed: int = 0,
    patience: int = 60,
    on_generation: Callable[[int, int], None] | None = None,
) -> tuple[np.ndarray, pd.DataFrame, float]:
    """Evolve plans from a greedy seed. Returns the best chromosome, a per-generation log and seconds."""
    if not hasattr(creator, "Plan"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Plan", list, fitness=creator.FitnessMax)
    # DEAP's selection and crossover draw from the global `random` module, so seed it too.
    random.seed(seed)
    np_rng = np.random.default_rng(seed)
    n = len(problem.slot_options)
    upper = np.array([len(o) for o in problem.slot_options])

    def make(genes):
        genes = repair(problem, np.asarray(genes), limits) if use_repair else np.asarray(genes)
        ind = creator.Plan(genes.tolist())
        value = objective(problem, chosen(problem, genes), beta, decay)
        ind.fitness.values = (value - (0.0 if use_repair else penalty(problem, genes, limits)),)
        return ind

    def mutate(genes):
        """Each gene changes with probability mutations_per_child / n, to any option or no contact."""
        genes = np.array(genes)
        hit = np.flatnonzero(np_rng.random(n) < mutations_per_child / n)
        genes[hit] = np_rng.integers(0, upper[hit] + 1)
        return genes

    # Greedy seeding: the greedy plan, mutated copies of it, and sparse random plans for diversity.
    pop = [make(seed_genes)] + [make(mutate(seed_genes)) for _ in range(pop_size // 2 - 1)]
    pop += [
        make(np.where(np_rng.random(n) < 0.3, np_rng.integers(1, upper + 1), 0))
        for _ in range(pop_size - len(pop))
    ]
    log, best, stale, started = [], max(i.fitness.values[0] for i in pop), 0, time.perf_counter()
    for gen in range(generations):
        elites = tools.selBest(pop, elite)
        parents = [
            creator.Plan(p)
            for p in tools.selTournament(pop, pop_size - elite, tournsize=tournament)
        ]
        for a, b in zip(parents[::2], parents[1::2], strict=False):
            if random.random() < cx_prob:
                tools.cxUniform(a, b, indpb=0.5)
        pop = elites + [make(mutate(c)) for c in parents]
        values = np.array([i.fitness.values[0] for i in pop])
        log.append({"generation": gen, "best": values.max(), "mean": values.mean()})
        stale = 0 if values.max() > best + 1e-6 else stale + 1
        best = max(best, values.max())
        if on_generation:
            on_generation(gen + 1, generations)
        if stale >= patience:
            break
    return np.asarray(tools.selBest(pop, 1)[0]), pd.DataFrame(log), time.perf_counter() - started


def ga(
    options: pd.DataFrame,
    limits: Limits,
    seed: int | None = None,
    cohorts: pd.DataFrame | None = None,
    **settings,
) -> pd.DataFrame:
    """The GA as a planner: same inputs and output as the baselines (a subset of option rows)."""
    seed = get_settings().anchorai_seed if seed is None else seed
    problem = build_problem(options, load_cohorts() if cohorts is None else cohorts, limits)
    start = encode(problem, options.index.get_indexer(greedy_uplift(options, limits).index))
    genes, _, _ = run_ga(problem, limits, start, seed=seed, **settings)
    return options.iloc[chosen(problem, genes)]

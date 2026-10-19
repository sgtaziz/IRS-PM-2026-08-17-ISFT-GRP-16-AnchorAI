"""Exact planning with CP-SAT (PLAN B3) and the random-instance generator (PLAN B1).

Evidence: notebooks/b_exact.ipynb (E5).
"""

import time

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

from anchorai.optimisation.ga import Problem
from anchorai.optimisation.model import TRAINER, Limits

SCALE, W = 100, 10_000  # money in cents; rank weights in 1/10,000
WORKERS = 8


def _solve(model: cp_model.CpModel, time_limit: float) -> tuple[cp_model.CpSolver, str, float]:
    solver = cp_model.CpSolver()
    solver.parameters.num_workers, solver.parameters.max_time_in_seconds = WORKERS, time_limit
    started = time.perf_counter()
    status = solver.Solve(model)
    return solver, solver.StatusName(status), time.perf_counter() - started


def solve_linear(
    options: pd.DataFrame, limits: Limits, time_limit: float = 60
) -> tuple[pd.DataFrame, str, float]:
    """Exact optimum of the linear objective: a multiple-choice knapsack with side limits."""
    m = cp_model.CpModel()
    x = [m.NewBoolVar("") for _ in range(len(options))]
    for idx in options.groupby("member_id").indices.values():
        m.Add(sum(x[i] for i in idx) <= 1)
    cost = np.round(options["cost"].to_numpy() * SCALE).astype(int)
    minutes = options["staff_minutes"].to_numpy().astype(int)
    trainer = np.flatnonzero((options["required_skill"] == TRAINER).to_numpy())
    m.Add(sum(int(cost[i]) * x[i] for i in range(len(x))) <= int(np.round(limits.budget * SCALE)))
    m.Add(sum(int(minutes[i]) * x[i] for i in range(len(x))) <= limits.staff_minutes)
    m.Add(sum(int(minutes[i]) * x[i] for i in trainer) <= limits.trainer_minutes)
    for offer_id, stock in limits.stock.items():
        offered = np.flatnonzero((options["offer_id"] == offer_id).to_numpy())
        m.Add(sum(x[i] for i in offered) <= stock)
    value = np.round(options["value"].to_numpy() * SCALE).astype(int)
    m.Maximize(sum(int(value[i]) * x[i] for i in range(len(x))))
    solver, status, seconds = _solve(m, time_limit)
    if status not in ("OPTIMAL", "FEASIBLE"):
        return options.iloc[:0], status, seconds
    plan = options.iloc[[i for i in range(len(x)) if solver.Value(x[i])]]
    return plan, status, seconds


def solve_full(
    problem: Problem, limits: Limits, beta: float, decay: float, time_limit: float = 60
) -> tuple[np.ndarray, str, float, float]:
    """Exact optimum of the GA's full objective; practical for about 50 members.

    Spillover: products of yes/no variables. Diminishing returns: each contacted member in an instructor
    group takes one rank slot weighted 1 / (1 + d·(r − 1)); with falling weights the best assignment is the
    sorted one, so maximising reproduces the GA's objective exactly. Returns the chromosome, the status,
    seconds and the best bound (dollars).
    """
    m = cp_model.CpModel()
    n_opt, n_slot = len(problem.cost), len(problem.slot_options)
    x = [m.NewBoolVar("") for _ in range(n_opt)]
    y = []
    for opts in problem.slot_options:
        y.append(m.NewBoolVar(""))
        m.Add(sum(x[i] for i in opts) == y[-1])
    cost = np.round(problem.cost * SCALE).astype(int)
    m.Add(sum(int(cost[i]) * x[i] for i in range(n_opt)) <= int(np.round(limits.budget * SCALE)))
    m.Add(sum(int(problem.minutes[i]) * x[i] for i in range(n_opt)) <= limits.staff_minutes)
    trainer = np.flatnonzero(problem.trainer)
    m.Add(sum(int(problem.minutes[i]) * x[i] for i in trainer) <= limits.trainer_minutes)
    for k, stock in enumerate(problem.stock):
        if np.isfinite(stock):
            m.Add(sum(x[i] for i in np.flatnonzero(problem.offer == k)) <= int(stock))
    spill = (
        problem.share @ problem.member_class.T
    )  # spill[s, t]: share member s gets from classmate t
    np.fill_diagonal(spill, 0.0)
    big = int(np.abs(problem.gross).max() * (1 + beta * spill.sum(1).max()) * SCALE) + 1
    value = []
    for s, opts in enumerate(problem.slot_options):
        terms = [int(np.round(problem.gross[i] * SCALE)) * x[i] for i in opts]
        for t in np.flatnonzero(spill[s] > 0) if beta else []:
            for i in opts:
                both = m.NewBoolVar("")
                m.AddMultiplicationEquality(both, [x[i], y[t]])
                terms.append(int(np.round(beta * spill[s, t] * problem.gross[i] * SCALE)) * both)
        value.append(sum(terms))
    terms = [-W * int(cost[i]) * x[i] for i in range(n_opt)]
    grouped = problem.group >= 0 if decay else np.zeros(n_slot, bool)
    terms += [W * value[s] for s in np.flatnonzero(~grouped)]
    for g in np.unique(problem.group[grouped]):
        members = np.flatnonzero(grouped & (problem.group == g))
        z = {(s, r): m.NewBoolVar("") for s in members for r in range(len(members))}
        for s in members:
            m.Add(sum(z[s, r] for r in range(len(members))) == y[s])
        for r in range(len(members)):
            m.Add(sum(z[s, r] for s in members) <= 1)
            for s in members:
                t = m.NewIntVar(-big, big, "")
                m.Add(t <= value[s])
                m.Add(t <= big * z[s, r])
                terms.append(int(np.round(W / (1 + decay * r))) * t)
    m.Maximize(sum(terms))
    solver, status, seconds = _solve(m, time_limit)
    genes = np.zeros(n_slot, int)
    if status in ("OPTIMAL", "FEASIBLE"):
        for s, opts in enumerate(problem.slot_options):
            for k, i in enumerate(opts):
                if solver.Value(x[i]):
                    genes[s] = k + 1
    return genes, status, seconds, solver.BestObjectiveBound() / (W * SCALE)


def exact(options: pd.DataFrame, limits: Limits, seed: int | None = None) -> pd.DataFrame:
    """CP-SAT as a planner on the linear objective: same inputs and output as the baselines."""
    return solve_linear(options, limits)[0]


def random_instance(
    options: pd.DataFrame, cohorts: pd.DataFrame, n_members: int, limits: Limits, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, Limits]:
    """Resample n real members (renamed) with their options and class rows; scale the limits to match."""
    rng = np.random.default_rng(seed)
    real = options["member_id"].unique()
    picked = rng.choice(real, size=n_members, replace=n_members > len(real))
    rename = {f"R{k:05d}": m for k, m in enumerate(picked)}
    by_member = dict(tuple(options.groupby("member_id")))
    rows = pd.concat(
        [by_member[m].assign(member_id=new) for new, m in rename.items()], ignore_index=True
    )
    in_class = dict(tuple(cohorts[cohorts["member_id"].isin(picked)].groupby("member_id")))
    classes = [in_class[m].assign(member_id=new) for new, m in rename.items() if m in in_class]
    coh = pd.concat(classes, ignore_index=True) if classes else cohorts.iloc[:0]
    share = n_members / len(real)
    scaled = Limits(
        limits.budget * share,
        int(limits.staff_minutes * share),
        int(limits.trainer_minutes * share),
        {o: max(1, int(s * share)) for o, s in limits.stock.items()},
    )
    return rows, coh, scaled

"""Regenerate the report's member-level figures as vector PDFs in the report's font and colours.

Run after `uv run anchorai data build` (and `anchorai setup` for the GA figure, which reads the app DB):

    cd SystemCode/backend && uv run python ../../ProjectReport/latex/scripts/figures.py [name ...]

Every figure uses the same package calls as its notebook, so the numbers match notebooks/results/.
"""

import sys
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from anchorai.config import get_settings
from anchorai.features import LABELS, SUSPECT, build_features
from anchorai.scenario.tables import read_tables

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parent.parent / "figures" / "generated"
OUT.mkdir(parents=True, exist_ok=True)
SEED = get_settings().anchorai_seed

BLUE, ORANGE, SKY, GREY, INK, MUTED, RULE = "#003D7C", "#EF7C00", "#6E9BD1", "#A3ADB8", "#1E2733", "#5C6773", "#C9D3DE"
TEXT_WIDTH = 158 / 25.4

# Text is typeset by LuaLaTeX in the report's own fonts, so figures and body text match exactly
mpl.use("pgf")
SANS = "/usr/share/texmf-dist/fonts/opentype/adobe/sourcesanspro/"
mpl.rcParams.update({
    "pgf.texsystem": "lualatex", "pgf.rcfonts": False,
    "pgf.preamble": "\\usepackage{fontspec}\\setmainfont{SourceSansPro}[Extension=.otf, UprightFont=*-Regular, "
                    "BoldFont=*-Semibold, ItalicFont=*-RegularIt, Path=" + SANS + "]",
    "font.family": "serif", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "legend.frameon": False,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "axes.grid": True, "grid.color": RULE, "grid.linewidth": 0.4, "axes.axisbelow": True,
    "axes.titleweight": "semibold", "axes.titlecolor": BLUE, "axes.titlelocation": "left",
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "axes.prop_cycle": mpl.cycler(color=[BLUE, ORANGE, SKY, GREY]),
})


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)
    print("wrote", name)


def data():
    tables = read_tables()
    labels = tables["members"].set_index("member_id")
    return tables, labels, build_features(tables["members"])


def trend_and_correlation():
    _, labels, features = data()
    fig, axes = plt.subplots(1, 2, figsize=(TEXT_WIDTH, 2.35), gridspec_kw={"width_ratios": [1, 1.15]})
    ax = axes[0]
    for churn, colour, name in ((0, BLUE, "stayed"), (1, ORANGE, "left")):
        ax.hist(features.loc[labels["churn"] == churn, "trend_ratio"], bins=40, range=(0, 2), density=True,
                color=colour, alpha=0.75, label=name, histtype="stepfilled", linewidth=0)
    ax.set_xlabel("visit trend (this month ÷ lifetime weekly visits)")
    ax.set_ylabel("density")
    ax.set_title("Attendance falls before members leave")
    ax.legend(loc="upper right")
    ax.grid(axis="x", visible=False)

    corr = features.assign(churn=labels["churn"]).corr()["churn"].drop("churn").sort_values()
    ax = axes[1]
    ax.barh([LABELS[c] for c in corr.index], corr.values, height=0.65,
            color=[ORANGE if c in SUSPECT else BLUE for c in corr.index])
    ax.set_xlabel("correlation with churn")
    ax.set_title("Feature correlation (orange: leakage suspects)")
    ax.tick_params(axis="y", labelsize=6.8)
    ax.grid(axis="y", visible=False)
    ax.axvline(0, color=MUTED, lw=0.6)
    fig.tight_layout(w_pad=2.2)
    save(fig, "trend_correlation")


def churn_figures():
    from sklearn.calibration import calibration_curve
    from sklearn.metrics import precision_recall_curve

    from anchorai.discovery import churn

    _, labels, features = data()
    result = churn.train(features, labels["churn"], labels["split"], SEED)
    test = (labels["split"] == "test").to_numpy()
    y, p = labels.loc[test, "churn"].to_numpy(), result.probabilities[test].to_numpy()
    raw = result.model.raw_proba(features[test])
    threshold = result.model.threshold

    fig, axes = plt.subplots(1, 3, figsize=(TEXT_WIDTH, 2.25))
    ax = axes[0]
    for score, name, colour in ((p, "AnchorAI ensemble", BLUE),
                                ((-features.loc[test, "avg_class_frequency_current_month"]).to_numpy(), "visits this month (ranked)", GREY)):
        prec, rec, _ = precision_recall_curve(y, score)
        ax.plot(rec, prec, color=colour, lw=1.3, label=name)
    op = (p >= threshold)
    ax.plot((op & (y == 1)).sum() / y.sum(), (op & (y == 1)).sum() / op.sum(), "o", color=ORANGE, ms=4.5,
            label=f"threshold {threshold:.3f}")
    ax.axhline(y.mean(), color=MUTED, lw=0.6, ls=":")
    ax.set(xlabel="recall", ylabel="precision", xlim=(0, 1.01), ylim=(0, 1.03), title="Precision–recall, test set")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 0.08))

    ax = axes[1]
    for probs, name, colour in ((raw, "before calibration", GREY), (p, "calibrated (served)", BLUE)):
        obs, pred = calibration_curve(y, probs, n_bins=10, strategy="quantile")
        ax.plot(pred, obs, marker="o", ms=3, lw=1.2, color=colour, label=name)
    ax.plot([0, 1], [0, 1], ls="--", color=MUTED, lw=0.7)
    ax.set(xlabel="predicted churn probability", ylabel="observed churn rate", title="Reliability, test set")
    ax.legend(loc="upper left")

    ax = axes[2]
    bins = np.linspace(0, 1, 21)
    ax.hist(p[y == 0], bins=bins, color=BLUE, alpha=0.8, label="stayed")
    ax.hist(p[y == 1], bins=bins, color=ORANGE, alpha=0.8, label="left")
    for cut in (0.3, 0.6):
        ax.axvline(cut, color=INK, lw=0.6, ls="--")
    ax.text(0.15, 0.97, "low", transform=ax.get_xaxis_transform(), ha="center", va="top", color=MUTED, fontsize=7)
    ax.text(0.45, 0.97, "medium", transform=ax.get_xaxis_transform(), ha="center", va="top", color=MUTED, fontsize=7)
    ax.text(0.8, 0.97, "high", transform=ax.get_xaxis_transform(), ha="center", va="top", color=MUTED, fontsize=7)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set(xlabel="churn probability", ylabel="test members (log scale)", title="Scores by outcome and band")
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, 0.88))
    fig.tight_layout(w_pad=1.6)
    save(fig, "churn_evaluation")

    import shap

    booster = result.model.lgbm[-1]
    x_test = features.loc[test, result.model.columns]
    values = shap.TreeExplainer(booster).shap_values(x_test.to_numpy())
    values = values[1] if isinstance(values, list) else values
    order = np.argsort(np.abs(values).mean(axis=0))[::-1][:10][::-1]
    cmap = LinearSegmentedColormap.from_list("nus", [BLUE, "#D9DEE5", ORANGE])
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH * 0.62, 2.9))
    rng = np.random.default_rng(SEED)
    for row, j in enumerate(order):
        v = x_test.iloc[:, j].to_numpy(dtype=float)
        lo, hi = np.nanpercentile(v, [5, 95])
        colour = np.clip((v - lo) / (hi - lo if hi > lo else 1), 0, 1)
        ax.scatter(values[:, j], row + rng.uniform(-0.28, 0.28, len(v)), c=colour, cmap=cmap, s=3.5, lw=0, alpha=0.85)
    ax.set_yticks(range(len(order)), [LABELS[result.model.columns[j]] for j in order], fontsize=7)
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_xlabel("contribution to churn log-odds (TreeSHAP, LightGBM member)")
    ax.set_title("What drives the churn score")
    ax.grid(axis="y", visible=False)
    sm = mpl.cm.ScalarMappable(cmap=cmap)
    cb = fig.colorbar(sm, ax=ax, pad=0.02, aspect=30)
    cb.set_ticks([0, 1], labels=["low", "high"])
    cb.set_label("feature value", fontsize=7)
    cb.outline.set_visible(False)
    save(fig, "shap")


def qini():
    from anchorai.discovery.uplift import t_learner

    tables, _, features = data()
    estimate = t_learner(features, tables["interventions"], list(tables["offers"]["offer_id"]), SEED)
    joined = tables["true_uplift"].merge(estimate, on=["member_id", "offer_id"], suffixes=("_true", "_est"))
    n = len(joined)
    x = np.arange(n + 1) / n

    def curve(score):
        return np.concatenate([[0], joined.sort_values(score, ascending=False)["uplift_true"].cumsum().to_numpy()])

    fig, ax = plt.subplots(figsize=(TEXT_WIDTH * 0.45, 2.3))
    ax.plot(x, curve("uplift_true"), color=GREY, lw=1.2, ls="--", label="oracle (true uplift)")
    ax.plot(x, curve("uplift_est"), color=BLUE, lw=1.4, label="T-learner")
    joined["random"] = np.random.default_rng(SEED).random(n)
    ax.plot(x, curve("random"), color=ORANGE, lw=1.1, label="random")
    ax.set(xlabel="share of member–offer pairs targeted", ylabel="members retained (true)", title="Qini curve")
    ax.legend(loc="lower right")
    save(fig, "qini")


def ga_convergence():
    from joblib import Parallel, delayed
    from sqlmodel import Session

    from anchorai.db.session import get_engine
    from anchorai.optimisation.baselines import greedy_uplift
    from anchorai.optimisation.ga import build_problem, chosen, encode, load_cohorts, objective, run_ga
    from anchorai.optimisation.model import load_instance

    instance = load_instance(Session(get_engine()))
    options, cohorts = instance.options, load_cohorts()
    week = instance.limits(1500, 72 * 60)
    problem = build_problem(options, cohorts, week)
    seed = encode(problem, options.index.get_indexer(greedy_uplift(options, week).index))
    runs = Parallel(n_jobs=5)(delayed(run_ga)(problem, week, seed, 0.5, 0.02, seed=s) for s in range(5))
    greedy_value = objective(problem, chosen(problem, seed))
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH * 0.5, 2.3))
    for s, (_, log, _) in enumerate(runs):
        ax.plot(log["generation"], log["best"], lw=1.1, color=BLUE, alpha=0.35 + 0.13 * s, label="GA, 5 seeds" if s == 0 else None)
    ax.axhline(greedy_value, color=ORANGE, lw=1.1, ls="--", label="greedy start")
    ax.set(xlabel="generation", ylabel="planner objective (dollars)", title="GA convergence: 72 staff hours, 1,500-dollar budget")
    ax.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.legend(loc="lower right")
    save(fig, "ga_convergence")
    finals = [objective(problem, chosen(problem, g)) for g, _, _ in runs]
    print("GA finals", [round(f, 1) for f in finals], "greedy", round(greedy_value, 1))


def base_hazard():
    from anchorai.scenario.build import base_churn

    _, labels, features = data()
    hazard = base_churn(features)
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH * 0.5, 2.2))
    ax.hist(hazard, bins=40, color=BLUE, alpha=0.9)
    ax.set(xlabel="no-contact churn hazard (synthetic)", ylabel="members", title="Scenario hazard")
    ax.grid(axis="x", visible=False)
    save(fig, "base_hazard")
    print("hazard range", round(float(hazard.min()), 3), round(float(hazard.max()), 3),
          "corr with label", round(float(np.corrcoef(hazard, labels["churn"])[0, 1]), 3))


FIGURES = {"trend": trend_and_correlation, "churn": churn_figures, "qini": qini, "ga": ga_convergence, "hazard": base_hazard}

if __name__ == "__main__":
    for name in sys.argv[1:] or FIGURES:
        FIGURES[name]()

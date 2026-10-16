"""Scenario layer: real Kaggle members plus a synthetic gym around them (docs/SCENARIO.md).

Only `members` (minus club_id, monthly_value and split) is real. Everything else is synthetic
and deterministic in the seed. The intervention history follows a documented ground-truth
effect function so uplift estimators and plans can be scored against it.
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from anchorai.features import build_features
from anchorai.scenario.offers import OFFER_CATALOG
from anchorai.scenario.tables import KAGGLE_COLUMNS, SchemaError

KAGGLE_URL = "https://www.kaggle.com/datasets/adrianvinueza/gym-customers-features-and-churn"
AS_OF = date(2026, 10, 12)
HISTORY_WEEKS = 12
CLUBS = ("C1", "C2", "C3")
INSTRUCTORS_PER_CLUB = 3
CLASSES_PER_INSTRUCTOR = 2
# Longer contracts are cheaper per month; Kaggle contract_period is 1, 6 or 12 months.
MONTHLY_PRICE = {1: 72.0, 6: 54.0, 12: 46.0}
INSTRUCTOR_NAMES = [
    "Sam Rivera", "Priya Nair", "Lee Wong", "Maya Chen", "Omar Haddad",
    "Ana Costa", "Tom Becker", "Nora Ali", "Ken Sato",
]  # fmt: skip
CLASS_NAMES = [
    "Spin", "HIIT", "Yoga", "Pilates", "Boxfit", "Circuit",
    "Zumba", "Core", "Stretch", "Bootcamp", "Barre", "Step",
    "Kettlebell", "Aqua", "Mobility", "TRX", "Dance", "Power",
]  # fmt: skip
OFFERS = pd.DataFrame(OFFER_CATALOG)[
    ["offer_id", "name", "cost", "staff_minutes", "inventory", "channels"]
].assign(channels=lambda d: d["channels"].str.join("|"))
HISTORY_SHARE = 0.6
TREATED_SHARE = 0.6


def find_raw_csv(raw_dir: Path) -> Path:
    found = sorted(raw_dir.glob("*.csv"))
    if len(found) != 1:
        raise FileNotFoundError(
            f"Expected exactly one Kaggle CSV in {raw_dir}, found {len(found)}. "
            f"Download it from {KAGGLE_URL}"
        )
    return found[0]


def load_kaggle(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = raw.columns.str.lower()
    missing = set(KAGGLE_COLUMNS) - set(raw.columns)
    if missing:
        raise SchemaError(f"{path.name}: missing Kaggle columns {sorted(missing)}")
    return raw[list(KAGGLE_COLUMNS)].astype(KAGGLE_COLUMNS)


def build_members(raw: pd.DataFrame, rng: np.random.Generator, seed: int) -> pd.DataFrame:
    members = raw.reset_index(drop=True)
    members.insert(0, "member_id", [f"M{i:04d}" for i in range(1, len(members) + 1)])
    members["club_id"] = rng.choice(CLUBS, size=len(members))
    members["monthly_value"] = members["contract_period"].map(MONTHLY_PRICE).fillna(60.0)
    _, test_idx = train_test_split(
        members.index, test_size=0.2, stratify=members["churn"], random_state=seed
    )
    members["split"] = "train"
    members.loc[test_idx, "split"] = "test"
    return members


def build_staff_and_classes() -> tuple[pd.DataFrame, pd.DataFrame]:
    instructors = pd.DataFrame(
        {
            "instructor_id": [f"I{i:02d}" for i in range(1, len(INSTRUCTOR_NAMES) + 1)],
            "name": INSTRUCTOR_NAMES,
            "club_id": np.repeat(CLUBS, INSTRUCTORS_PER_CLUB),
        }
    )
    classes = instructors.loc[
        instructors.index.repeat(CLASSES_PER_INSTRUCTOR), ["club_id", "instructor_id"]
    ].reset_index(drop=True)
    classes.insert(0, "class_id", [f"K{i:02d}" for i in range(1, len(classes) + 1)])
    classes.insert(1, "name", CLASS_NAMES[: len(classes)])
    return instructors, classes


def build_attendance(
    members: pd.DataFrame, classes: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Group-class members attend 1-3 classes at their club; visits sum to their Kaggle rate."""
    goers = members[members["group_visits"] == 1]
    n_classes = rng.integers(1, 4, size=len(goers))
    rows = goers.loc[goers.index.repeat(n_classes), ["member_id", "club_id"]]
    club_classes = np.stack(classes.groupby("club_id")["class_id"].apply(np.array)[list(CLUBS)])
    club_index = rows["club_id"].map({c: i for i, c in enumerate(CLUBS)}).to_numpy()
    pick = rng.integers(0, club_classes.shape[1], size=len(rows))
    rows["class_id"] = club_classes[club_index, pick]
    rows["weight"] = rng.random(len(rows))
    rows = rows.groupby(["member_id", "class_id"], as_index=False)["weight"].sum()
    rows["weight"] /= rows.groupby("member_id")["weight"].transform("sum")
    freq = members.set_index("member_id")["avg_class_frequency_total"]
    rows["visits_per_week"] = (rows["weight"] * rows["member_id"].map(freq)).round(3)
    # A member who never comes to class (or whose share rounds to nothing) does not attend it.
    return rows[rows["visits_per_week"] > 0].reset_index(drop=True)


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-z))


def base_churn(f: pd.DataFrame) -> pd.Series:
    """Synthetic no-contact churn hazard over the next month, from features only."""
    z = (
        -1.4
        + 1.3 * (f["lifetime"] <= 2)
        + 1.1 * (f["trend_ratio"] < 0.7)
        - 0.9 * (f["contract_period"] == 12)
        - 0.4 * f["group_visits"]
        - 0.5 * (f["avg_class_frequency_total"] - 1.9)
    )
    return pd.Series(sigmoid(z.to_numpy()), index=f.index, name="base_churn")


def offer_effects(f: pd.DataFrame) -> pd.DataFrame:
    """Raw treatment effect on next-month retention, one column per offer (before saturation).

    Effects are heterogeneous on purpose: PT sessions work for new members, class passes for
    class-goers, discounts for price-sensitive monthly members and backfire on annual ones.
    """
    falling = (f["trend_ratio"] < 0.85).astype(float)
    new = (f["lifetime"] <= 3).astype(float)
    price_sensitive = (f["contract_period"] == 1) & (f["avg_additional_charges_total"] < 120)
    effects = pd.DataFrame(
        {
            "checkin_message": 0.02 + 0.04 * falling,
            "free_pt_session": 0.02 + 0.14 * new + 0.04 * falling,
            "class_pass": 0.01 + 0.10 * f["group_visits"] + 0.04 * f["promo_friends"],
            "discount_1m": 0.01
            + 0.12 * price_sensitive.astype(float)
            - 0.06 * (f["contract_period"] == 12),
        },
        index=f.index,
    )
    # Persuasion matters more for members who are at risk in the first place.
    return effects.mul(0.6 + base_churn(f), axis=0)


def build_true_uplift(features: pd.DataFrame) -> pd.DataFrame:
    """Realised uplift in stay probability, after saturating at certain retention."""
    stay = 1 - base_churn(features)
    treated_stay = (offer_effects(features).add(stay, axis=0)).clip(0, 1)
    uplift = treated_stay.sub(stay, axis=0)
    long = (
        uplift.rename_axis("member_id")
        .reset_index()
        .melt(id_vars="member_id", var_name="offer_id", value_name="uplift")
    )
    return long.sort_values(["member_id", "offer_id"], ignore_index=True)


def build_interventions(
    members: pd.DataFrame,
    features: pd.DataFrame,
    true_uplift: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Randomised past contacts: a random share of members, a random offer, a random week."""
    history = members.sample(frac=HISTORY_SHARE, random_state=rng.integers(2**31))
    history = history.reset_index(drop=True)
    n = len(history)
    history["week_start"] = pd.to_datetime(AS_OF) - pd.to_timedelta(
        7 * rng.integers(1, HISTORY_WEEKS + 1, size=n), unit="D"
    )
    history["treated"] = rng.random(n) < TREATED_SHARE
    offer = pd.Series(rng.choice(OFFERS["offer_id"], size=n)).where(history["treated"])
    history["offer_id"] = offer
    options = OFFERS.assign(channel=OFFERS["channels"].str.split("|")).explode("channel")
    options["k"] = options.groupby("offer_id").cumcount()
    n_options = history["offer_id"].map(options.groupby("offer_id").size()).fillna(1)
    history["k"] = (rng.random(n) * n_options).astype(int)
    history = history.merge(options[["offer_id", "k", "channel"]], on=["offer_id", "k"], how="left")
    effect = history.merge(true_uplift, on=["member_id", "offer_id"], how="left")["uplift"]
    stay = 1 - history["member_id"].map(base_churn(features))
    history["stayed"] = rng.random(n) < (stay + effect.fillna(0)).clip(0, 1).to_numpy()
    history = history.sort_values(["week_start", "member_id"], ignore_index=True)
    history["intervention_id"] = [f"V{i:05d}" for i in range(1, n + 1)]
    return history


def build_events(classes: pd.DataFrame, attendance: pd.DataFrame) -> pd.DataFrame:
    """The busiest instructor leaves; the busiest class at another club is cancelled."""
    week = pd.Timestamp(AS_OF - timedelta(days=7))
    load = attendance.merge(classes, on="class_id").groupby(["club_id", "instructor_id"]).size()
    club, instructor = load.sort_values(ascending=False, kind="stable").index[0]
    others = attendance.merge(classes[classes["club_id"] != club], on="class_id")
    cancelled = others.groupby("class_id").size().sort_values(ascending=False, kind="stable")
    return pd.DataFrame(
        {
            "event_id": ["E001", "E002"],
            "event_type": ["instructor_left", "class_cancelled"],
            "entity_id": [instructor, cancelled.index[0]],
            "week_start": [week, week],
        }
    )


def build_tables(raw: pd.DataFrame, seed: int) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    members = build_members(raw, rng, seed)
    instructors, classes = build_staff_and_classes()
    attendance = build_attendance(members, classes, rng)
    features = build_features(members)
    true_uplift = build_true_uplift(features)
    return {
        "members": members,
        "instructors": instructors,
        "classes": classes,
        "attendance": attendance,
        "offers": OFFERS,
        "interventions": build_interventions(members, features, true_uplift, rng),
        "true_uplift": true_uplift,
        "events": build_events(classes, attendance),
    }

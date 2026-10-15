"""Scenario v0: real Kaggle members plus a crude synthetic gym around them.

Only `members` (minus club_id and monthly_value) is real. Everything else is synthetic and
deterministic in the seed. The intervention history and true uplift here are placeholders
until scenario v1 (PLAN.md A5) documents the ground-truth effect function.
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from anchorai.config import get_settings
from anchorai.scenario.tables import KAGGLE_COLUMNS, SchemaError, write_tables

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
OFFERS = pd.DataFrame(
    [
        ("checkin_message", "Personal check-in message", 0.0, 5, None, "sms|email"),
        ("free_pt_session", "Free personal training session", 40.0, 60, 40, "call|in_person"),
        ("class_pass", "Bring-a-friend class pass", 15.0, 10, 100, "sms|email|call"),
        ("discount_1m", "One month at 20% off", 12.0, 15, None, "email|call"),
    ],
    columns=["offer_id", "name", "cost", "staff_minutes", "inventory", "channels"],
)
OFFER_BASE_UPLIFT = {
    "checkin_message": 0.02,
    "free_pt_session": 0.08,
    "class_pass": 0.05,
    "discount_1m": 0.04,
}


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
    by_club = classes.groupby("club_id")["class_id"].apply(list)
    pick = rng.integers(0, len(classes) // len(CLUBS), size=len(rows))
    rows["class_id"] = [by_club[c][i] for c, i in zip(rows["club_id"], pick, strict=True)]
    rows["weight"] = rng.random(len(rows))
    rows = rows.groupby(["member_id", "class_id"], as_index=False)["weight"].sum()
    rows["weight"] /= rows.groupby("member_id")["weight"].transform("sum")
    freq = members.set_index("member_id")["avg_class_frequency_total"]
    rows["visits_per_week"] = (rows["weight"] * rows["member_id"].map(freq)).round(3)
    return rows


def build_true_uplift(members: pd.DataFrame) -> pd.DataFrame:
    """Crude v0 effect: larger for churners, with a few offer-specific modifiers."""
    grid = members.merge(OFFERS[["offer_id"]], how="cross")
    risk = np.where(grid["churn"] == 1, 1.0, 0.3)
    uplift = grid["offer_id"].map(OFFER_BASE_UPLIFT) * risk
    uplift += np.where((grid["offer_id"] == "free_pt_session") & (grid["lifetime"] <= 3), 0.05, 0)
    uplift += np.where((grid["offer_id"] == "class_pass") & (grid["group_visits"] == 1), 0.03, 0)
    uplift += np.where(
        (grid["offer_id"] == "discount_1m") & (grid["contract_period"] == 1), 0.03, 0
    )
    grid["uplift"] = uplift.round(4)
    return grid[["member_id", "offer_id", "uplift"]]


def build_interventions(
    members: pd.DataFrame, true_uplift: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    history = members.sample(frac=0.3, random_state=rng.integers(2**31)).reset_index(drop=True)
    n = len(history)
    history["week_start"] = pd.to_datetime(AS_OF) - pd.to_timedelta(
        7 * rng.integers(1, HISTORY_WEEKS + 1, size=n), unit="D"
    )
    history["treated"] = rng.random(n) < 0.6
    offer = pd.Series(rng.choice(OFFERS["offer_id"], size=n)).where(history["treated"])
    history["offer_id"] = offer
    channels = OFFERS.set_index("offer_id")["channels"].str.split("|")
    history["channel"] = [
        rng.choice(channels[o]) if isinstance(o, str) else None for o in history["offer_id"]
    ]
    effect = history.merge(true_uplift, on=["member_id", "offer_id"], how="left")["uplift"]
    p_stay = np.where(history["churn"] == 1, 0.3, 0.9) + effect.fillna(0).to_numpy()
    history["stayed"] = rng.random(n) < np.clip(p_stay, 0, 1)
    history = history.sort_values(["week_start", "member_id"], ignore_index=True)
    history["intervention_id"] = [f"V{i:05d}" for i in range(1, n + 1)]
    return history


def build_events(instructors: pd.DataFrame, classes: pd.DataFrame) -> pd.DataFrame:
    week = pd.Timestamp(AS_OF - timedelta(days=7))
    return pd.DataFrame(
        {
            "event_id": ["E001", "E002"],
            "event_type": ["instructor_left", "class_cancelled"],
            "entity_id": [instructors["instructor_id"].iloc[0], classes["class_id"].iloc[-1]],
            "week_start": [week, week],
        }
    )


def build_tables(raw: pd.DataFrame, seed: int) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    members = build_members(raw, rng, seed)
    instructors, classes = build_staff_and_classes()
    true_uplift = build_true_uplift(members)
    return {
        "members": members,
        "instructors": instructors,
        "classes": classes,
        "attendance": build_attendance(members, classes, rng),
        "offers": OFFERS,
        "interventions": build_interventions(members, true_uplift, rng),
        "true_uplift": true_uplift,
        "events": build_events(instructors, classes),
    }


def build(seed: int | None = None) -> Path:
    """Regenerate every data table from data/raw/ into data/generated/."""
    settings = get_settings()
    seed = settings.anchorai_seed if seed is None else seed
    raw = load_kaggle(find_raw_csv(settings.anchorai_data_dir / "raw"))
    out = settings.anchorai_data_dir / "generated"
    write_tables(build_tables(raw, seed), out)
    return out

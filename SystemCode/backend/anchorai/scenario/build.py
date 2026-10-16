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
# Log-odds added to the no-contact churn hazard per unit share of a member's weekly class
# visits hit by the event (docs/SCENARIO.md). Losing the instructor you train with is the
# larger shock; a cancelled class leaves the rest of the routine intact.
EVENT_EFFECTS = {"instructor_left": 1.4, "class_cancelled": 0.9}


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


def base_logit(f: pd.DataFrame) -> pd.Series:
    """Log-odds of the synthetic no-contact churn hazard over the next month, from features."""
    return (
        -1.4
        + 1.3 * (f["lifetime"] <= 2)
        + 1.1 * (f["trend_ratio"] < 0.7)
        - 0.9 * (f["contract_period"] == 12)
        - 0.4 * f["group_visits"]
        - 0.5 * (f["avg_class_frequency_total"] - 1.9)
    ).rename("base_logit")


def base_churn(f: pd.DataFrame) -> pd.Series:
    """Synthetic no-contact churn hazard over the next month, before any gym event."""
    return pd.Series(sigmoid(base_logit(f).to_numpy()), index=f.index, name="base_churn")


def event_exposure(
    attendance: pd.DataFrame, classes: pd.DataFrame, events: pd.DataFrame
) -> pd.DataFrame:
    """Share of each member's weekly class visits hit by each kind of event.

    Mirrors the knowledge graph's definitions: the share of visits in classes whose instructor
    left, and in classes that were cancelled. Members without class visits are not listed.
    """
    visits = attendance.merge(classes[["class_id", "instructor_id"]], on="class_id")
    total = visits.groupby("member_id")["visits_per_week"].sum()
    total = total[total > 0]
    gone = events.loc[events["event_type"] == "instructor_left", "entity_id"]
    cancelled = events.loc[events["event_type"] == "class_cancelled", "entity_id"]

    def share(hit: pd.Series) -> pd.Series:
        lost = visits[hit].groupby("member_id")["visits_per_week"].sum()
        return (lost / total).reindex(total.index).fillna(0.0)

    return pd.DataFrame(
        {
            "lost_instructor_share": share(visits["instructor_id"].isin(gone)),
            "cancelled_share": share(visits["class_id"].isin(cancelled)),
        }
    ).rename_axis("member_id")


def event_shift(exposure: pd.DataFrame, index: pd.Index, effects: dict[str, float]) -> pd.Series:
    """Log-odds added to each member's hazard by the events in `exposure`."""
    exposure = exposure.reindex(index).fillna(0.0)
    return (
        effects["instructor_left"] * exposure["lost_instructor_share"]
        + effects["class_cancelled"] * exposure["cancelled_share"]
    )


def raw_offer_effects(f: pd.DataFrame) -> pd.DataFrame:
    """Raw treatment effect on next-month retention, one column per offer, before risk scaling.

    Effects are heterogeneous on purpose: PT sessions work for new members, class passes for
    class-goers, discounts for price-sensitive monthly members and backfire on annual ones.
    """
    falling = (f["trend_ratio"] < 0.85).astype(float)
    new = (f["lifetime"] <= 3).astype(float)
    price_sensitive = (f["contract_period"] == 1) & (f["avg_additional_charges_total"] < 120)
    return pd.DataFrame(
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


def realised_uplift(raw: pd.DataFrame, hazard: pd.Series) -> pd.DataFrame:
    """Uplift in stay probability at a given hazard, saturating at certain retention."""
    # Persuasion matters more for members who are at risk in the first place.
    stay = 1 - hazard
    treated_stay = raw.mul(0.6 + hazard, axis=0).add(stay, axis=0).clip(0, 1)
    return treated_stay.sub(stay, axis=0)


def build_true_churn(
    features: pd.DataFrame,
    exposure: pd.DataFrame,
    rng: np.random.Generator,
    effects: dict[str, float],
) -> pd.DataFrame:
    """Next-month churn without contact, before and after the gym events, plus one draw of it."""
    logit = base_logit(features)
    shares = exposure.reindex(features.index).fillna(0.0)
    event = sigmoid((logit + event_shift(exposure, features.index, effects)).to_numpy())
    return pd.DataFrame(
        {
            "member_id": features.index,
            "base_churn": sigmoid(logit.to_numpy()),
            "event_churn": event,
            "lost_instructor_share": shares["lost_instructor_share"].to_numpy(),
            "cancelled_share": shares["cancelled_share"].to_numpy(),
            "churned_no_contact": rng.random(len(features)) < event,
        }
    )


def build_true_uplift(features: pd.DataFrame, hazard: pd.Series) -> pd.DataFrame:
    """Realised uplift for contacting each member now, at their post-event hazard."""
    uplift = realised_uplift(raw_offer_effects(features), hazard)
    long = (
        uplift.rename_axis("member_id")
        .reset_index()
        .melt(id_vars="member_id", var_name="offer_id", value_name="uplift")
    )
    return long.sort_values(["member_id", "offer_id"], ignore_index=True)


def build_interventions(
    members: pd.DataFrame,
    features: pd.DataFrame,
    attendance: pd.DataFrame,
    classes: pd.DataFrame,
    events: pd.DataFrame,
    rng: np.random.Generator,
    effects: dict[str, float],
) -> pd.DataFrame:
    """Randomised past contacts: a random share of members, a random offer, a random week.

    Each outcome uses the hazard in force that week, so an event only affects contacts made
    in or after the week it happened.
    """
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

    logit = history["member_id"].map(base_logit(features))
    for week in history["week_start"].unique():
        happened = events[events["week_start"] <= week]
        if happened.empty:
            continue
        shift = event_shift(event_exposure(attendance, classes, happened), features.index, effects)
        in_week = history["week_start"] == week
        logit[in_week] += history.loc[in_week, "member_id"].map(shift)
    hazard = pd.Series(sigmoid(logit.to_numpy()), index=history.index)
    raw = raw_offer_effects(features).loc[history["member_id"]].set_index(history.index)
    uplift = realised_uplift(raw, hazard)
    treated = np.flatnonzero(history["treated"].to_numpy())
    column = history["offer_id"].map({c: i for i, c in enumerate(uplift.columns)})
    effect = np.zeros(n)
    effect[treated] = uplift.to_numpy()[treated, column.to_numpy()[treated].astype(int)]
    history["stayed"] = rng.random(n) < np.clip(1 - hazard.to_numpy() + effect, 0, 1)
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


def build_tables(
    raw: pd.DataFrame, seed: int, event_effects: dict[str, float] | None = None
) -> dict[str, pd.DataFrame]:
    effects = EVENT_EFFECTS if event_effects is None else event_effects
    rng = np.random.default_rng(seed)
    members = build_members(raw, rng, seed)
    instructors, classes = build_staff_and_classes()
    attendance = build_attendance(members, classes, rng)
    features = build_features(members)
    events = build_events(classes, attendance)
    interventions = build_interventions(
        members, features, attendance, classes, events, rng, effects
    )
    exposure = event_exposure(attendance, classes, events)
    true_churn = build_true_churn(features, exposure, rng, effects)
    hazard = true_churn.set_index("member_id")["event_churn"]
    return {
        "members": members,
        "instructors": instructors,
        "classes": classes,
        "attendance": attendance,
        "offers": OFFERS,
        "interventions": interventions,
        "true_uplift": build_true_uplift(features, hazard),
        "true_churn": true_churn,
        "events": events,
    }

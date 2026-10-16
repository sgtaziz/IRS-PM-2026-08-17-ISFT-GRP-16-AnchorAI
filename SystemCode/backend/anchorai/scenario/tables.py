"""Data-table contract shared by all streams (docs/PLAN.md §6).

Each table is a parquet file in `<data_dir>/generated/` (or a CSV in `tests/fixtures/`) whose
columns and dtypes are fixed here. Change a schema only with agreement from all three streams.
"""

from pathlib import Path

import pandas as pd

from anchorai.config import get_settings

KAGGLE_COLUMNS: dict[str, str] = {
    "gender": "int64",
    "near_location": "int64",
    "partner": "int64",
    "promo_friends": "int64",
    "phone": "int64",
    "contract_period": "int64",
    "group_visits": "int64",
    "age": "int64",
    "avg_additional_charges_total": "float64",
    "month_to_end_contract": "float64",
    "lifetime": "int64",
    "avg_class_frequency_total": "float64",
    "avg_class_frequency_current_month": "float64",
    "churn": "int64",
}

SCHEMAS: dict[str, dict[str, str]] = {
    "members": {
        "member_id": "string",
        **KAGGLE_COLUMNS,
        "club_id": "string",
        "monthly_value": "float64",
        # "train" or "test": the stratified 80/20 split; never fit anything on "test".
        "split": "string",
    },
    "instructors": {
        "instructor_id": "string",
        "name": "string",
        "club_id": "string",
    },
    "classes": {
        "class_id": "string",
        "name": "string",
        "club_id": "string",
        "instructor_id": "string",
    },
    "attendance": {
        "member_id": "string",
        "class_id": "string",
        "visits_per_week": "float64",
    },
    "offers": {
        "offer_id": "string",
        "name": "string",
        "cost": "float64",
        "staff_minutes": "int64",
        "inventory": "Int64",
        # Allowed anchorai.schemas.Channel values, "|"-separated.
        "channels": "string",
    },
    "interventions": {
        "intervention_id": "string",
        "member_id": "string",
        "week_start": "datetime64[ns]",
        # Null offer_id and channel when treated is false (the control group).
        "offer_id": "string",
        "channel": "string",
        "treated": "bool",
        "stayed": "bool",
    },
    "true_uplift": {
        "member_id": "string",
        "offer_id": "string",
        "uplift": "float64",
    },
    "true_churn": {
        "member_id": "string",
        # Scenario-only ground truth: next-month churn probability without any contact.
        "base_churn": "float64",
        "event_churn": "float64",
        "lost_instructor_share": "float64",
        "cancelled_share": "float64",
        # One seeded draw of the no-contact outcome, for rates rather than probabilities.
        "churned_no_contact": "bool",
    },
    "events": {
        "event_id": "string",
        "event_type": "string",
        "entity_id": "string",
        "week_start": "datetime64[ns]",
    },
}

EVENT_TYPES = ("instructor_left", "class_cancelled")

PRIMARY_KEYS: dict[str, list[str]] = {
    "members": ["member_id"],
    "instructors": ["instructor_id"],
    "classes": ["class_id"],
    "attendance": ["member_id", "class_id"],
    "offers": ["offer_id"],
    "interventions": ["intervention_id"],
    "true_uplift": ["member_id", "offer_id"],
    "true_churn": ["member_id"],
    "events": ["event_id"],
}

FOREIGN_KEYS: list[tuple[str, str, str]] = [
    ("classes", "instructor_id", "instructors"),
    ("attendance", "member_id", "members"),
    ("attendance", "class_id", "classes"),
    ("interventions", "member_id", "members"),
    ("interventions", "offer_id", "offers"),
    ("true_uplift", "member_id", "members"),
    ("true_uplift", "offer_id", "offers"),
    ("true_churn", "member_id", "members"),
]


class SchemaError(ValueError):
    pass


def conform(name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Return `df` with exactly the contract columns, in order, cast to the contract dtypes."""
    schema = SCHEMAS[name]
    missing = set(schema) - set(df.columns)
    if missing:
        raise SchemaError(f"{name}: missing columns {sorted(missing)}")
    return df[list(schema)].astype(schema).reset_index(drop=True)


def check_integrity(tables: dict[str, pd.DataFrame]) -> None:
    """Raise SchemaError on duplicate keys or dangling foreign keys across the tables."""
    for name, keys in PRIMARY_KEYS.items():
        if tables[name].duplicated(keys).any():
            raise SchemaError(f"{name}: duplicate key {keys}")
    for name, column, target in FOREIGN_KEYS:
        values = tables[name][column].dropna()
        dangling = set(values) - set(tables[target][PRIMARY_KEYS[target][0]])
        if dangling:
            raise SchemaError(f"{name}.{column}: unknown {target} {sorted(dangling)[:5]}")
    if (tables["attendance"]["visits_per_week"] <= 0).any():
        raise SchemaError("attendance: every row needs visits_per_week > 0")
    events = tables["events"]
    if not events["event_type"].isin(EVENT_TYPES).all():
        raise SchemaError(f"events: event_type must be one of {EVENT_TYPES}")


def generated_dir() -> Path:
    return get_settings().anchorai_data_dir / "generated"


def read_tables(directory: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load every table from parquet (or CSV, for fixtures), conformed to the contract."""
    directory = directory or generated_dir()
    tables = {}
    for name, schema in SCHEMAS.items():
        parquet, csv = directory / f"{name}.parquet", directory / f"{name}.csv"
        if parquet.exists():
            df = pd.read_parquet(parquet)
        elif csv.exists():
            dates = [c for c, t in schema.items() if t.startswith("datetime")]
            df = pd.read_csv(csv, dtype={"member_id": str}, parse_dates=dates)
        else:
            raise FileNotFoundError(f"No {name}.parquet or {name}.csv in {directory}")
        tables[name] = conform(name, df)
    return tables


def write_tables(tables: dict[str, pd.DataFrame], directory: Path | None = None) -> None:
    directory = directory or generated_dir()
    directory.mkdir(parents=True, exist_ok=True)
    conformed = {name: conform(name, tables[name]) for name in SCHEMAS}
    check_integrity(conformed)
    for name, df in conformed.items():
        df.to_parquet(directory / f"{name}.parquet", index=False)

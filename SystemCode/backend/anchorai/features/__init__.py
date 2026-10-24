import numpy as np
import pandas as pd

CATEGORICAL = [
    "gender",
    "near_location",
    "partner",
    "promo_friends",
    "phone",
    "group_visits",
    "contract_period",
]
NUMERIC = [
    "age",
    "avg_additional_charges_total",
    "lifetime",
    "avg_class_frequency_total",
    "charges_per_month",
    "month_to_end_contract",
    "contract_progress",
    "avg_class_frequency_current_month",
    "trend_ratio",
    "visit_change",
]
FEATURES = CATEGORICAL + NUMERIC
# Possibly measured in the same month as the churn label, plus
# everything derived from them. The leakage check trains with and without this set.
SUSPECT = [
    "month_to_end_contract",
    "contract_progress",
    "avg_class_frequency_current_month",
    "trend_ratio",
    "visit_change",
]

LABELS = {
    "gender": "Gender",
    "near_location": "Lives or works nearby",
    "partner": "Partner-company employee",
    "promo_friends": "Joined via a friend",
    "phone": "Phone on file",
    "group_visits": "Attends group classes",
    "contract_period": "Contract length (months)",
    "age": "Age",
    "avg_additional_charges_total": "Extra spend",
    "lifetime": "Months as a member",
    "avg_class_frequency_total": "Lifetime visits per week",
    "charges_per_month": "Extra spend per month",
    "month_to_end_contract": "Months left on contract",
    "contract_progress": "Share of contract used",
    "avg_class_frequency_current_month": "Visits per week this month",
    "trend_ratio": "Visit trend (this month vs lifetime)",
    "visit_change": "Change in weekly visits (this month vs lifetime)",
}


def build_features(members: pd.DataFrame) -> pd.DataFrame:
    """Model-ready features indexed by member_id; no label, no synthetic columns."""
    m = members.set_index("member_id")
    total = m["avg_class_frequency_total"]
    current = m["avg_class_frequency_current_month"]
    f = m[[c for c in FEATURES if c in m.columns]].astype(float)
    # Members with no lifetime visits have no trend; treat them as flat rather than infinite.
    f["trend_ratio"] = np.where(total > 0, current / total.where(total > 0), 1.0).clip(0, 3)
    # Signed so the label reads true: negative means fewer visits this month than usual.
    f["visit_change"] = current - total
    f["contract_progress"] = (1 - m["month_to_end_contract"] / m["contract_period"]).clip(0, 1)
    f["charges_per_month"] = m["avg_additional_charges_total"] / (m["lifetime"] + 1)
    return f[FEATURES]

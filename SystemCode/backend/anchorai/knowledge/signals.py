"""KG cohort signals as rule facts, cached to parquet so the pipeline runs without Neo4j."""

from pathlib import Path
from typing import Any

import pandas as pd
from neo4j import Driver

from anchorai.knowledge import queries
from anchorai.knowledge.graph import read
from anchorai.scenario.tables import generated_dir

KG_FACTS_FILE = "kg_facts.parquet"
# Chosen in notebooks/c_kg.ipynb.
ANCHOR_SHARE_THRESHOLD = 0.5
COHORT_RISK_THRESHOLD = 0.5
KG_COLUMNS = ["anchor_instructor_share", "lost_anchor_instructor", "class_cancelled", "cohort_risk"]


def compute_kg_facts(driver: Driver | None = None) -> pd.DataFrame:
    """One row per member with any KG signal, indexed by member_id."""

    def frame(query: str) -> pd.DataFrame:
        rows = read(query, driver)
        return pd.DataFrame(rows).set_index("member_id") if rows else pd.DataFrame()

    share = frame(queries.ANCHOR_SHARE)
    cancelled = frame(queries.CLASS_CANCELLED).assign(class_cancelled=True)
    cohort = frame(queries.COHORT_RISK)
    facts = pd.concat([share, cancelled, cohort], axis=1).reindex(columns=KG_COLUMNS)
    facts["anchor_instructor_share"] = facts["anchor_instructor_share"].astype(float)
    facts["lost_anchor_instructor"] = facts["anchor_instructor_share"] >= ANCHOR_SHARE_THRESHOLD
    facts["class_cancelled"] = facts["class_cancelled"].fillna(False).astype(bool)
    facts["cohort_risk"] = facts["cohort_risk"].astype(float)
    return facts.rename_axis("member_id")


def kg_facts_path(directory: Path | None = None) -> Path:
    return (directory or generated_dir()) / KG_FACTS_FILE


def save_kg_facts(facts: pd.DataFrame, directory: Path | None = None) -> Path:
    path = kg_facts_path(directory)
    facts.reset_index().to_parquet(path, index=False)
    return path


def load_kg_facts(directory: Path | None = None) -> pd.DataFrame | None:
    """Cached KG facts, or None when the graph has never been loaded."""
    path = kg_facts_path(directory)
    if not path.exists():
        return None
    return pd.read_parquet(path).set_index("member_id")


def graph_signals(facts: dict[str, Any]) -> list[str]:
    """Plain-English KG signals for one member, for `Explanation.graph_signals`."""
    signals = []
    if facts.get("lost_anchor_instructor"):
        share = facts["anchor_instructor_share"]
        signals.append(f"{share:.0%} of their class visits were with an instructor who has left")
    if facts.get("class_cancelled"):
        signals.append("A class they attend has been cancelled")
    cohort = facts.get("cohort_risk")
    if cohort is not None and cohort >= COHORT_RISK_THRESHOLD:
        signals.append(f"Their class cohort's average churn risk is {cohort:.0%}")
    return signals

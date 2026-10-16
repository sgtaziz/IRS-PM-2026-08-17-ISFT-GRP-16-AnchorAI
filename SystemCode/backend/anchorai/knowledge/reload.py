"""Reload Neo4j from the effective tables and recompute the cached KG facts.

Takes about a second on the demo data, so callers wait for it instead of running a job.
"""

import threading
from datetime import UTC, datetime

from pydantic import BaseModel

from anchorai.discovery.scores import load_scores
from anchorai.knowledge.entities import effective_tables
from anchorai.knowledge.graph import GraphUnavailable, get_driver, neo4j_available
from anchorai.knowledge.loader import load_graph
from anchorai.knowledge.signals import compute_kg_facts, save_kg_facts
from anchorai.scenario.tables import generated_dir


class GraphDown(RuntimeError):
    pass


class KgStatus(BaseModel):
    """`stale` is true when an edit was saved but the graph could not be rebuilt from it."""

    stale: bool = False
    last_reloaded_at: str | None = None
    error: str | None = None
    counts: dict[str, int] | None = None


_lock = threading.Lock()
_status = KgStatus()


def status() -> KgStatus:
    return _status.model_copy()


def reload_graph() -> dict[str, int]:
    """Rebuild the graph and cache its facts; raises `GraphDown` when Neo4j can't be reached."""
    driver = get_driver()
    if not neo4j_available(driver):
        raise GraphDown("Neo4j is not reachable")
    scores = load_scores() if (generated_dir() / "member_scores.parquet").exists() else None
    try:
        counts = load_graph(driver, effective_tables(), scores)
        save_kg_facts(compute_kg_facts(driver))
    except GraphUnavailable as e:
        raise GraphDown("Neo4j went away during the reload") from e
    return counts


def sync_graph() -> KgStatus:
    """Reload and record the outcome; never raises, so a saved edit is not lost to a down graph."""
    global _status
    with _lock:
        try:
            counts = reload_graph()
        except GraphDown as e:
            _status = _status.model_copy(update={"stale": True, "error": str(e)})
        else:
            now = datetime.now(UTC).isoformat(timespec="seconds")
            _status = KgStatus(last_reloaded_at=now, counts=counts)
        return _status.model_copy()

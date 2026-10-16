"""Reload Neo4j from the effective tables and recompute the cached KG facts.

Takes about a second on the demo data, so callers wait for it instead of running a job.
"""

import threading
from datetime import UTC, datetime

from neo4j.exceptions import Neo4jError
from pydantic import BaseModel
from sqlmodel import Session, func, select

from anchorai.db.models import AuditLog
from anchorai.discovery.scores import load_scores
from anchorai.discovery.service import DataNotBuilt
from anchorai.knowledge.entities import effective_tables
from anchorai.knowledge.graph import GraphUnavailable, get_driver, neo4j_available
from anchorai.knowledge.loader import load_graph
from anchorai.knowledge.signals import compute_kg_facts, kg_facts_path, save_kg_facts
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


def edits_unapplied(session: Session) -> bool:
    """True when a gym edit was saved after the cached KG facts were written (survives restarts)."""
    last_edit = session.exec(
        select(func.max(AuditLog.ts)).where(AuditLog.action.like("gym.%"))
    ).one()
    if last_edit is None:
        return False
    path = kg_facts_path()
    if not path.exists():
        return True
    if last_edit.tzinfo is None:
        last_edit = last_edit.replace(tzinfo=UTC)
    return last_edit.timestamp() > path.stat().st_mtime


def status(session: Session) -> KgStatus:
    current = _status.model_copy()
    if not current.stale and edits_unapplied(session):
        current.stale = True
        current.error = "Edits were saved after the graph was last loaded"
    return current


def reload_graph(session: Session | None = None) -> dict[str, int]:
    """Rebuild the graph and cache its facts; raises `GraphDown` when Neo4j can't be reached."""
    driver = get_driver()
    if not neo4j_available(driver):
        raise GraphDown("Neo4j is not reachable")
    scores = load_scores() if (generated_dir() / "member_scores.parquet").exists() else None
    try:
        counts = load_graph(driver, effective_tables(session), scores)
        save_kg_facts(compute_kg_facts(driver))
    except (*GraphUnavailable, Neo4jError) as e:
        # The graph may be half loaded: callers keep it marked stale until a reload succeeds.
        raise GraphDown(f"The graph reload failed ({type(e).__name__})") from e
    except DataNotBuilt as e:
        raise GraphDown(str(e)) from e
    return counts


def sync_graph(session: Session | None = None) -> KgStatus:
    """Reload and record the outcome; never raises, so a saved edit is not lost to a down graph."""
    global _status
    with _lock:
        try:
            counts = reload_graph(session)
        except GraphDown as e:
            _status = _status.model_copy(update={"stale": True, "error": str(e)})
        else:
            now = datetime.now(UTC).isoformat(timespec="seconds")
            _status = KgStatus(last_reloaded_at=now, counts=counts)
        return _status.model_copy()

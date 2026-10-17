"""Reload Neo4j from the effective tables and recompute the cached KG facts.

Takes about a second on the demo data, so callers wait for it instead of running a job.
"""

import logging
import threading
from datetime import UTC, datetime

import pandas as pd
from neo4j.exceptions import AuthError, ConfigurationError, Neo4jError
from pydantic import BaseModel
from sqlmodel import Session, func, select

from anchorai import catalog
from anchorai.db.models import AuditLog
from anchorai.db.session import get_engine
from anchorai.discovery.scores import load_scores
from anchorai.discovery.service import DataNotBuilt
from anchorai.knowledge.entities import effective_tables
from anchorai.knowledge.graph import GraphUnavailable, get_driver, neo4j_available, reloading
from anchorai.knowledge.loader import load_graph
from anchorai.knowledge.signals import (
    compute_kg_facts,
    facts_problem,
    kg_facts_path,
    save_kg_facts,
)
from anchorai.scenario.tables import generated_dir

log = logging.getLogger(__name__)


class GraphDown(RuntimeError):
    pass


class GraphUnreachable(GraphDown):
    """Neo4j can't be reached at all, as opposed to a load that failed."""


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
    if not current.stale:
        problem = facts_problem()
        if problem:
            current.stale, current.error = True, problem
        elif edits_unapplied(session):
            current.stale = True
            current.error = "Edits were saved after the graph was last loaded"
    return current


def _catalog_offers(session: Session | None) -> pd.DataFrame:
    # Inactive offers stay in: past interventions link to their Offer nodes.
    if session is None:
        with Session(get_engine()) as own:
            return _catalog_offers(own)
    return pd.DataFrame(
        [o.model_dump(include={"offer_id", "name", "cost"}) for o in catalog.list_offers(session)]
    )


def reload_graph(session: Session | None = None) -> dict[str, int]:
    """Rebuild the graph and cache its facts.

    Raises `GraphUnreachable` when Neo4j can't be reached and `GraphDown` for any other failure.
    """
    try:
        driver = get_driver()
        reachable = neo4j_available(driver)
    except AuthError as e:
        raise GraphDown(
            "Neo4j rejected the credentials; check NEO4J_USER and NEO4J_PASSWORD"
        ) from e
    except ConfigurationError as e:
        raise GraphDown(f"NEO4J_URI is not valid: {e}") from e
    if not reachable:
        raise GraphUnreachable("Neo4j is not reachable")
    scores = load_scores() if (generated_dir() / "member_scores.parquet").exists() else None
    reloading.set()
    try:
        tables = effective_tables(session)
        offers = _catalog_offers(session)
        if not offers.empty:
            tables["offers"] = offers
        counts = load_graph(driver, tables, scores)
        save_kg_facts(compute_kg_facts(driver))
    except (*GraphUnavailable, Neo4jError) as e:
        # The graph may be half loaded: callers keep it marked stale until a reload succeeds.
        raise GraphDown(f"The graph reload failed ({type(e).__name__}: {e})") from e
    except DataNotBuilt as e:
        raise GraphDown(str(e)) from e
    finally:
        reloading.clear()
    return counts


def sync_graph(session: Session | None = None) -> KgStatus:
    """Reload and record the outcome; never raises, so a saved edit is not lost to a down graph."""
    global _status
    with _lock:
        try:
            counts = reload_graph(session)
        except GraphDown as e:
            _status = _status.model_copy(update={"stale": True, "error": str(e)})
        except Exception as e:
            log.exception("knowledge graph reload failed")
            error = f"The graph reload failed ({type(e).__name__})"
            _status = _status.model_copy(update={"stale": True, "error": error})
        else:
            now = datetime.now(UTC).isoformat(timespec="seconds")
            _status = KgStatus(last_reloaded_at=now, counts=counts)
        return _status.model_copy()

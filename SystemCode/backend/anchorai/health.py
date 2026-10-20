"""System health for the admin Settings page (W45): LLM, knowledge graph, models, database and planner."""

import json
import time

from alembic.runtime.migration import MigrationContext
from sqlmodel import Session, col, select

from anchorai.assistant import llm
from anchorai.config import get_settings
from anchorai.db import models
from anchorai.db.migrate import heads
from anchorai.knowledge import reload
from anchorai.knowledge.graph import neo4j_available
from anchorai.optimisation.contacts import logged_cases
from anchorai.scenario.tables import generated_dir, read_tables


def _masked(key: str) -> str | None:
    if not key:
        return None
    return f"…{key[-4:]}" if len(key) > 8 else "set"


def _models() -> dict:
    card_path = generated_dir() / "model_card.json"
    if not card_path.exists():
        return {"built": False}
    card = json.loads(card_path.read_text())
    test = card.get("churn", {}).get("test", {})
    return {
        "built": True,
        "built_at": card.get("built_at"),
        "seed": card.get("seed"),
        "members": card.get("n_members"),
        "churn_model": card.get("churn", {}).get("model"),
        "churn_test": {k: test.get(k) for k in ("f1", "pr_auc", "brier")},
        "uplift_baseline": card.get("uplift", {}).get("method"),
    }


def details(session: Session) -> dict:
    s = get_settings()
    kg = reload.status(session)
    current = MigrationContext.configure(session.connection()).get_current_revision()
    latest = heads()
    plan = session.exec(select(models.Plan).order_by(col(models.Plan.created_at).desc())).first()
    try:
        randomised = len(read_tables()["interventions"])
    except FileNotFoundError:
        randomised = None
    return {
        "status": "ok",
        "llm": {
            "base_url": s.llm_base_url,
            "model": s.llm_model,
            "api_key": _masked(s.llm_api_key),
            "tool_calling": s.llm_tool_calling,
        },
        "knowledge_graph": {
            "uri": s.neo4j_uri,
            "reachable": neo4j_available(),
            "stale": kg.stale,
            "problem": kg.error,
            "last_reloaded_at": kg.last_reloaded_at,
            "counts": kg.counts,
        },
        "models": _models(),
        "database": {
            "revision": current,
            "latest": latest,
            "up_to_date": current in latest,
        },
        "planner": {
            "latest_plan": None
            if plan is None
            else {"id": plan.id, "status": plan.status, "created_at": plan.created_at.isoformat()},
            "uplift_source": "cbr",
            "case_base": {"randomised": randomised, "logged": len(logged_cases(session))},
        },
    }


def test_llm() -> dict:
    """One tiny request to the configured endpoint; never raises."""
    started = time.perf_counter()
    try:
        reply = llm.chat([{"role": "user", "content": "Reply with the word OK."}], max_tokens=5)
    except Exception as exc:  # noqa: BLE001  any client or network failure is the answer here
        return {"ok": False, "seconds": round(time.perf_counter() - started, 2), "error": str(exc)}
    return {
        "ok": True,
        "seconds": round(time.perf_counter() - started, 2),
        "reply": reply.strip()[:40],
    }

import os

import pandas as pd
import pytest
from neo4j.exceptions import AuthError
from sqlmodel import Session
from typer.testing import CliRunner

from anchorai import cli
from anchorai.knowledge import graph, reload
from anchorai.knowledge.graph import GraphReloading
from anchorai.knowledge.reload import GraphDown, GraphUnreachable
from anchorai.knowledge.signals import KG_COLUMNS, kg_facts_path, save_kg_facts
from anchorai.scenario.tables import generated_dir


@pytest.fixture(autouse=True)
def fresh_status(monkeypatch):
    monkeypatch.setattr(reload, "_status", reload.KgStatus())


def write_facts(newer_than_card: bool) -> None:
    facts = pd.DataFrame(columns=["member_id", *KG_COLUMNS]).set_index("member_id")
    save_kg_facts(facts)
    card = generated_dir() / "model_card.json"
    card.touch()
    now = kg_facts_path().stat().st_mtime
    os.utime(card, (now, now + (-10 if newer_than_card else 10)))


def test_status_is_stale_when_the_cached_facts_are_missing_or_predate_the_data(built, engine):
    with Session(engine) as session:
        assert "not been loaded" in reload.status(session).error
        write_facts(newer_than_card=False)
        assert "before the last data build" in reload.status(session).error
        write_facts(newer_than_card=True)
        assert reload.status(session).stale is False


def test_simulate_flags_a_graph_with_dropped_facts(built, engine):
    from anchorai.knowledge import simulate

    write_facts(newer_than_card=False)
    with Session(engine) as session:
        assert reload.status(session).stale is True
        assert simulate.reload.status(session).stale is True


def test_reads_fail_fast_while_a_reload_is_running(monkeypatch):
    monkeypatch.setattr(graph, "get_driver", lambda: pytest.fail("no connection expected"))
    graph.reloading.set()
    try:
        with pytest.raises(GraphReloading):
            graph.read("RETURN 1")
        with pytest.raises(GraphReloading):
            graph.read_records("RETURN 1")
    finally:
        graph.reloading.clear()


def test_sync_graph_marks_stale_instead_of_raising(monkeypatch):
    def bad_uri():
        raise RuntimeError("bad uri")

    monkeypatch.setattr(reload, "get_driver", bad_uri)
    result = reload.sync_graph()
    assert result.stale is True
    assert "RuntimeError" in result.error


@pytest.mark.parametrize(
    ("failure", "code", "text"),
    [
        (GraphUnreachable("Neo4j is not reachable"), 0, "skipped"),
        (GraphDown("model card missing"), 1, "model card missing"),
    ],
)
def test_kg_load_only_skips_when_neo4j_is_unreachable(built, monkeypatch, failure, code, text):
    def fail():
        raise failure

    monkeypatch.setattr(cli, "reload_graph", fail)
    result = CliRunner().invoke(cli.app, ["kg", "load"])
    assert result.exit_code == code
    assert text in result.output


def test_wrong_credentials_are_not_reported_as_unreachable(monkeypatch):
    def refused(_):
        raise AuthError("unauthorised")

    monkeypatch.setattr(reload, "get_driver", lambda: object())
    monkeypatch.setattr(reload, "neo4j_available", refused)
    with pytest.raises(GraphDown, match="credentials") as e:
        reload.reload_graph()
    assert not isinstance(e.value, GraphUnreachable)

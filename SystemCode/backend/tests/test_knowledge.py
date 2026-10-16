import os

import pandas as pd
import pytest
from neo4j.exceptions import ServiceUnavailable

from anchorai.discovery import service
from anchorai.knowledge import loader, signals
from anchorai.reasoning.facts import build_facts
from anchorai.scenario.tables import read_tables
from tests.conftest import FIXTURES


class FakeTx:
    def __init__(self, calls):
        self.calls = calls

    def run(self, query, parameters=None, **params):
        self.calls.append((query, params))
        return self

    def consume(self):
        return None


class FakeDriver:
    def __init__(self):
        self.calls = []

    def session(self, **_):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def run(self, query, **params):
        return FakeTx(self.calls).run(query, **params)

    def execute_write(self, work):
        return work(FakeTx(self.calls))


def test_loader_only_sends_values_as_parameters():
    driver = FakeDriver()
    counts = loader.load_graph(driver, read_tables(FIXTURES))
    assert counts["members"] == 12 and counts["attendance"] == 8 and counts["events"] == 2
    templates = {loader.CLEAR, *loader.CONSTRAINTS} | {
        getattr(loader, n)
        for n in dir(loader)
        if n.isupper() and isinstance(getattr(loader, n), str)
    }
    assert all(q in templates for q, _ in driver.calls)
    member_rows = next(p["rows"] for q, p in driver.calls if q == loader.MEMBERS)
    assert member_rows[0]["member_id"] == "M0001" and "props" in member_rows[0]


def test_kg_facts_cache_and_rule_facts(tmp_path, built):
    assert signals.load_kg_facts(tmp_path) is None
    facts = pd.DataFrame(
        {
            "anchor_instructor_share": [1.0],
            "lost_anchor_instructor": [True],
            "class_cancelled": [False],
            "cohort_risk": [0.7],
        },
        index=pd.Index(["M0002"], name="member_id"),
    )
    signals.save_kg_facts(facts, tmp_path)
    cached = signals.load_kg_facts(tmp_path)

    data = service.get_data()
    by_member = build_facts(data.table, data.features, data.tables["interventions"], cached)
    assert by_member["M0002"]["lost_anchor_instructor"] is True
    # Members without a KG signal get explicit False, not a missing fact.
    assert by_member["M0001"]["lost_anchor_instructor"] is False
    assert "anchor_instructor_share" not in by_member["M0001"]
    lines = signals.graph_signals(by_member["M0002"])
    assert lines == ["100% of their class visits were with an instructor who has left"]

    # A data build after the graph load makes the cached facts stale.
    (tmp_path / "model_card.json").write_text("{}")
    assert signals.load_kg_facts(tmp_path) is None


def test_ego_endpoint_degrades_when_graph_is_down(client, login, monkeypatch):
    def down(member_id):
        raise ServiceUnavailable("down")

    monkeypatch.setattr("anchorai.api.routers.graph.ego_graph", down)
    assert client.get("/api/graph/ego/M0001", headers=login("staff1")).status_code == 503


@pytest.mark.skipif(
    not os.environ.get("ANCHORAI_NEO4J_TESTS"),
    reason="set ANCHORAI_NEO4J_TESTS=1 to run against a live Neo4j (clears the graph)",
)
def test_live_graph_signals_on_fixtures():
    from anchorai.knowledge.ego import ego_graph
    from anchorai.knowledge.graph import get_driver

    loader.load_graph(get_driver(), read_tables(FIXTURES))
    facts = signals.compute_kg_facts()
    assert facts.loc["M0002", "anchor_instructor_share"] == 1.0
    assert facts.loc["M0002", "lost_anchor_instructor"]
    assert facts.loc[["M0004", "M0007"], "class_cancelled"].all()
    graph = ego_graph("M0002")
    assert {n.data["type"] for n in graph.nodes} >= {"Member", "Club", "Class", "Instructor"}

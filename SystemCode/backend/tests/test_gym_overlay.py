from datetime import date

import pytest
from sqlmodel import Session, select

from anchorai.db.models import AuditLog, ClassInstructorOverride, GymClass, GymEvent, GymInstructor
from anchorai.knowledge import reload
from anchorai.knowledge.entities import merge
from anchorai.knowledge.reload import GraphDown
from anchorai.scenario.tables import read_tables
from tests.conftest import FIXTURES


def test_overlay_merge():
    tables = read_tables(FIXTURES)
    eff = merge(
        tables,
        instructors=[GymInstructor(instructor_id="IX01", name="New Coach", club_id="C1")],
        classes=[GymClass(class_id="KX01", name="Barre", club_id="C1", instructor_id="IX01")],
        overrides=[ClassInstructorOverride(class_id="K03", instructor_id="IX01")],
        events=[
            GymEvent(id=1, event_type="instructor_left", entity_id="I01", week_start=date.today(),
                     suppresses="E001"),
            GymEvent(id=2, event_type="class_cancelled", entity_id="KX01", week_start=date.today()),
        ],
    )  # fmt: skip
    classes = eff.classes.set_index("class_id")
    assert classes.loc["KX01", "source"] == "added"
    assert classes.loc["K03", "instructor_id"] == "IX01"
    assert classes.loc["K01", "instructor_id"] == "I01"
    events = eff.events.set_index("event_id")
    assert "E001" not in events.index and "E002" in events.index
    assert events.loc["EX002", "entity_id"] == "KX01"
    assert "IX01" in set(eff.instructors["instructor_id"])


@pytest.fixture
def graph_down(monkeypatch):
    def down():
        raise GraphDown("Neo4j is not reachable")

    monkeypatch.setattr(reload, "reload_graph", down)


def test_edit_is_saved_when_graph_is_down(built, client, login, engine, graph_down):
    manager = login("manager")
    r = client.post(
        "/api/admin/gym/instructors", json={"name": "Ana", "club_id": "C1"}, headers=manager
    )
    assert r.status_code == 201
    new_id = r.json()["id"]
    assert r.json()["kg"]["stale"] is True

    body = {"event_type": "instructor_left", "entity_id": new_id, "note": "moved away"}
    assert client.post("/api/admin/gym/events", json=body, headers=manager).status_code == 201
    assert client.post("/api/admin/gym/events", json=body, headers=manager).status_code == 409

    roster = client.get("/api/admin/gym", headers=manager).json()
    ana = next(i for i in roster["instructors"] if i["id"] == new_id)
    assert ana["status"] == "left" and ana["source"] == "added"

    r = client.post("/api/admin/kg/reload", headers=manager)
    assert r.status_code == 503 and "not reachable" in r.json()["detail"]
    assert any(
        i["id"] == new_id
        for i in client.get("/api/admin/gym", headers=manager).json()["instructors"]
    )

    with Session(engine) as session:
        actions = session.exec(select(AuditLog.action).where(AuditLog.action.like("gym.%"))).all()
    assert {"gym.instructor_add", "gym.event_record"} <= set(actions)


def test_roles_and_revoking_a_generated_event(built, client, login, graph_down):
    assert client.get("/api/admin/gym", headers=login("staff1")).status_code == 403
    assert client.post("/api/admin/kg/reload", headers=login("staff1")).status_code == 403

    admin = login("admin")
    assert client.delete("/api/admin/gym/events/E002", headers=admin).status_code == 200
    classes = {c["id"]: c for c in client.get("/api/admin/gym", headers=admin).json()["classes"]}
    assert classes["K04"]["status"] == "active"
    assert client.delete("/api/admin/gym/events/E002", headers=admin).status_code == 404

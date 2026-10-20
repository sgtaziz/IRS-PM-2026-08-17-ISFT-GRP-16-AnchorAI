from anchorai import health as system
from anchorai.config import get_settings


def test_admin_health_details_never_expose_the_llm_key(client, login, built, monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_api_key", "sk-secret-value-1234")
    monkeypatch.setattr(system, "neo4j_available", lambda: False)
    r = client.get("/api/health/details", headers=login("admin"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "sk-secret" not in r.text and body["llm"]["api_key"] == "…1234"
    assert body["knowledge_graph"]["reachable"] is False
    # The test DB is built from the models, not by migrations, so it has no revision to compare.
    assert set(body["database"]) == {"revision", "latest", "up_to_date"}
    assert body["models"]["built"] is True
    assert client.post("/api/health/llm-test", headers=login("manager")).status_code == 403


def test_llm_connection_test_reports_success_and_failure(client, login, monkeypatch):
    admin = login("admin")
    monkeypatch.setattr(system.llm, "chat", lambda messages, **kw: "OK")
    assert client.post("/api/health/llm-test", headers=admin).json()["ok"] is True

    def down(messages, **kw):
        raise ConnectionError("Connection error.")

    monkeypatch.setattr(system.llm, "chat", down)
    result = client.post("/api/health/llm-test", headers=admin).json()
    assert result["ok"] is False and "Connection error" in result["error"]

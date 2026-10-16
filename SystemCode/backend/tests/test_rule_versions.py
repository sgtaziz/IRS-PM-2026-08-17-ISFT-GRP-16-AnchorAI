from anchorai.reasoning.engine import load_rule_files, load_rules
from anchorai.reasoning.versions import dump_rules


def test_dump_round_trips_the_shipped_rules():
    rules = load_rule_files()
    rules[3] = rules[3].model_copy(update={"enabled": False})
    assert load_rules(dump_rules(rules)) == rules


def test_save_enable_and_rollback_are_versioned_and_audited(client, login):
    admin = login("admin")
    text = client.get("/api/rules/versions/1", headers=admin).json()["yaml_text"]

    no_source = text.replace("source: team assumption", "source: ''", 1)
    r = client.post("/api/rules/validate", json={"yaml_text": no_source}, headers=admin)
    assert r.json()["parse_errors"]
    body = {"yaml_text": no_source, "note": "bad"}
    assert client.put("/api/rules", json=body, headers=admin).status_code == 422
    assert (
        client.put("/api/rules", json={"yaml_text": text, "note": ""}, headers=admin).status_code
        == 422
    )

    r = client.patch(
        "/api/rules/G04_low_risk_no_paid_offers", json={"enabled": False}, headers=admin
    )
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["is_active"]
    rules = {x["id"]: x for x in client.get("/api/rules", headers=admin).json()["rules"]}
    assert rules["G04_low_risk_no_paid_offers"]["enabled"] is False
    assert client.patch("/api/rules/NOPE", json={"enabled": True}, headers=admin).status_code == 404

    versions = client.get("/api/rules/versions", headers=admin).json()
    assert [v["version"] for v in versions if v["is_active"]] == [2]

    assert client.post("/api/rules/versions/1/activate", headers=admin).status_code == 200
    rules = {x["id"]: x for x in client.get("/api/rules", headers=admin).json()["rules"]}
    assert rules["G04_low_risk_no_paid_offers"]["enabled"] is True

    actions = client.get("/api/admin/audit", headers=admin).json()["actions"]
    assert {"rule_disable", "rule_version_activate"} <= set(actions)
    assert (
        client.put(
            "/api/rules", json={"yaml_text": text, "note": "x"}, headers=login("manager")
        ).status_code
        == 403
    )

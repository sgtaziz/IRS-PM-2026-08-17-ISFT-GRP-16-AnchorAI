from sqlmodel import Session, func, select

from anchorai.db.models import RuleVersion
from anchorai.reasoning.engine import load_rule_files, load_rules
from anchorai.reasoning.versions import dump_rules


def test_dump_round_trips_the_shipped_rules():
    rules = load_rule_files()
    rules[3] = rules[3].model_copy(update={"enabled": False})
    assert load_rules(dump_rules(rules)) == rules


def _active(client, headers) -> int:
    versions = client.get("/api/rules/versions", headers=headers).json()
    return next(v["version"] for v in versions if v["is_active"])


def test_save_enable_and_rollback_are_versioned_and_audited(client, login):
    admin = login("admin")
    text = client.get("/api/rules/versions/1", headers=admin).json()["yaml_text"]

    no_source = text.replace("source: team assumption", "source: ''", 1)
    r = client.post("/api/rules/validate", json={"yaml_text": no_source}, headers=admin)
    assert r.json()["parse_errors"]
    body = {"yaml_text": no_source, "note": "bad", "base_version": 1}
    assert client.put("/api/rules", json=body, headers=admin).status_code == 422
    body = {"yaml_text": text, "note": "", "base_version": 1}
    assert client.put("/api/rules", json=body, headers=admin).status_code == 422

    change = {"enabled": False, "base_version": 1}
    r = client.patch("/api/rules/G04_low_risk_no_paid_offers", json=change, headers=admin)
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["is_active"]
    rules = {x["id"]: x for x in client.get("/api/rules", headers=admin).json()["rules"]}
    assert rules["G04_low_risk_no_paid_offers"]["enabled"] is False
    missing = {"enabled": True, "base_version": 2}
    assert client.patch("/api/rules/NOPE", json=missing, headers=admin).status_code == 404

    # A second editor still holding version 1 must not overwrite version 2.
    stale = {"yaml_text": text, "note": "stale", "base_version": 1}
    assert client.put("/api/rules", json=stale, headers=admin).status_code == 409
    assert (
        client.patch("/api/rules/G01_contact_fatigue", json=change, headers=admin).status_code
        == 409
    )
    assert (
        client.post(
            "/api/rules/versions/1/activate", json={"base_version": 1}, headers=admin
        ).status_code
        == 409
    )

    r = client.post("/api/rules/versions/1/activate", json={"base_version": 2}, headers=admin)
    assert r.status_code == 200
    rules = {x["id"]: x for x in client.get("/api/rules", headers=admin).json()["rules"]}
    assert rules["G04_low_risk_no_paid_offers"]["enabled"] is True

    actions = client.get("/api/admin/audit", headers=admin).json()["actions"]
    assert {"rule_disable", "rule_version_activate"} <= set(actions)
    body = {"yaml_text": text, "note": "x", "base_version": 1}
    assert client.put("/api/rules", json=body, headers=login("manager")).status_code == 403


def test_rollback_checks_the_version_and_a_broken_active_one_can_be_replaced(client, login, engine):
    admin = login("admin")
    good = client.get("/api/rules/versions/1", headers=admin).json()["yaml_text"]
    base = _active(client, admin)
    with Session(engine) as session:
        top = session.exec(select(func.max(RuleVersion.version))).one()
        session.add(
            RuleVersion(
                version=top + 1,
                yaml_text=good.replace("days_since_last_contact", "made_up_fact", 1),
            )
        )
        session.add(RuleVersion(version=top + 2, yaml_text="not: [valid"))
        session.commit()
    bad_unknown_fact, bad_yaml = top + 1, top + 2
    r = client.post(
        f"/api/rules/versions/{bad_unknown_fact}/activate",
        json={"base_version": base},
        headers=admin,
    )
    assert r.status_code == 422 and r.json()["detail"]["issues"]
    assert _active(client, admin) == base

    with Session(engine) as session:
        for v in session.exec(select(RuleVersion)).all():
            v.is_active = v.version == bad_yaml
            session.add(v)
        session.commit()
    change = {"enabled": False, "base_version": bad_yaml}
    assert (
        client.patch("/api/rules/G01_contact_fatigue", json=change, headers=admin).status_code
        == 422
    )
    body = {"yaml_text": good, "note": "recover", "base_version": bad_yaml}
    assert client.put("/api/rules", json=body, headers=admin).status_code == 200

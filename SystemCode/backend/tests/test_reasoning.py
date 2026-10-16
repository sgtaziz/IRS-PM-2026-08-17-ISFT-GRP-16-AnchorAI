import pytest
from pydantic import ValidationError

from anchorai.discovery import service
from anchorai.reasoning.conditions import parse_condition
from anchorai.reasoning.engine import load_rule_files, load_rules, run
from anchorai.reasoning.facts import KNOWN_FACTS, build_facts
from anchorai.reasoning.validate import validate
from anchorai.scenario.offers import OFFER_CATALOG
from anchorai.schemas import Channel

OFFERS = [o["offer_id"] for o in OFFER_CATALOG]
CHANNELS = [c.value for c in Channel]

RULES = """
- id: D_low
  kind: derive
  salience: 10
  description: low trend
  when: ["trend_ratio < 0.5"]
  then: {assert: {pattern: slipping}}
  source: test
- id: P_generic
  kind: playbook
  salience: 20
  description: generic check-in
  when: ["pattern == slipping"]
  then: {propose: {offer_id: checkin_message, channel: sms}}
  source: test
- id: P_specific
  kind: playbook
  salience: 20
  description: slipping and new
  when: ["pattern == slipping", "lifetime <= 3"]
  then: {propose: {offer_id: free_pt_session, channel: call}}
  source: test
- id: G_discount
  kind: guardrail
  salience: 100
  description: discount only month-to-month
  when: ["contract_period != 1"]
  then: {block: [discount_1m]}
  source: test
- id: P_discount
  kind: playbook
  salience: 5
  description: discount
  when: ["pattern == slipping"]
  then: {propose: {offer_id: discount_1m, channel: email}}
  source: test
"""


def test_conflict_resolution_and_chaining():
    out = run(load_rules(RULES), {"trend_ratio": 0.3, "lifetime": 2, "contract_period": 12})
    order = [f.rule_id for f in out.firings]
    # Guardrail by salience, the derive enables both playbooks, specificity breaks the tie.
    assert order == ["G_discount", "D_low", "P_specific", "P_generic", "P_discount"]
    assert out.facts["pattern"] == "slipping"
    assert out.blocked == {"discount_1m": "G_discount"}
    assert [p.offer_id for p in out.allowed] == ["free_pt_session", "checkin_message"]
    assert out.firings[1].facts_matched == {"trend_ratio": 0.3}


def test_block_all_and_missing_facts():
    rules = load_rules(
        RULES
        + """
- id: G_fatigue
  kind: guardrail
  salience: 100
  description: fatigue
  when: ["days_since_last_contact < 30"]
  then: {block: all}
  source: test
"""
    )
    blocked = run(rules, {"trend_ratio": 0.3, "lifetime": 9, "days_since_last_contact": 7})
    assert blocked.allowed == [] and blocked.blocked["all"] == "G_fatigue"
    # Never contacted: the fact is absent, so the guardrail does not match.
    assert run(rules, {"trend_ratio": 0.3, "lifetime": 9}).allowed


def test_conditions_parse_safely():
    assert parse_condition("segment in [New and slipping, 'x']").holds({"segment": "x"})
    assert parse_condition("churn_prob > 1e-1").value == 0.1
    assert not parse_condition("churn_prob >= 0.5").holds({"churn_prob": "high"})
    # Booleans and numbers never match each other, unlike Python's True == 1.
    assert not parse_condition("group_visits == 1").holds({"group_visits": True})
    assert not parse_condition("flag == true").holds({"flag": 1})
    for bad in [
        "__import__('os') == 1",
        "x >= ",
        "a ~ 1",
        "a in 3",
        "a == [1]",
        "a > yes",
        "d == 2026-01-01",
    ]:
        with pytest.raises(ValueError):
            parse_condition(bad)
    with pytest.raises(ValidationError):
        load_rules(
            "- {id: x, kind: derive, description: d, when: [a > 1], then: {block: all}, source: s}"
        )
    with pytest.raises(ValidationError):
        load_rules(
            "- {id: x, kind: guardrail, description: d, when: [a > 1], then: {block: []}, source: s}"
        )


def test_duplicate_ids_rejected_and_first_assertion_wins():
    rule = "- {{id: {id}, kind: derive, salience: {s}, description: d, when: [a > 0], then: {{assert: {{tier: {v}}}}}, source: s}}\n"
    with pytest.raises(ValueError, match="Duplicate"):
        load_rules(rule.format(id="x", s=1, v="a") + rule.format(id="x", s=2, v="b"))
    rules = load_rules(rule.format(id="hi", s=90, v="hot") + rule.format(id="lo", s=10, v="cold"))
    out = run(rules, {"a": 1})
    assert out.facts["tier"] == "hot"
    assert out.firings[1].effect == "assert (kept existing tier)"


def test_validator_finds_author_errors():
    rules = load_rules(
        """
- id: A
  kind: derive
  description: a
  when: ["churn_prob >= 0.5"]
  then: {assert: {tier: hot}}
  source: s
- id: B
  kind: derive
  description: b
  when: ["churn_prob > 0.4", "churn_prob < 0.9"]
  then: {assert: {tier: warm}}
  source: s
- id: C
  kind: playbook
  description: c
  when: ["tier == cold", "made_up_fact > 1"]
  then: {propose: {offer_id: nope, channel: pigeon}}
  source: s
- id: D
  kind: derive
  description: disjoint from A
  when: ["churn_prob < 0.2"]
  then: {assert: {tier: cool}}
  source: s
- id: E
  kind: derive
  description: only ever churn_prob == 1, which F excludes
  when: ["churn_prob >= 1", "churn_prob <= 1"]
  then: {assert: {band: top}}
  source: s
- id: F
  kind: derive
  description: overwrites an input fact
  when: ["churn_prob != 1"]
  then: {assert: {band: other, risk_band: low}}
  source: s
"""
    )
    messages = {
        (i.rule_id, i.message.split(" ")[0]) for i in validate(rules, KNOWN_FACTS, OFFERS, CHANNELS)
    }
    assert ("A", "Contradicts") in messages and ("D", "Contradicts") not in messages
    assert {("C", "Unknown"), ("C", "Unreachable:")} <= messages
    assert ("E", "Contradicts") not in messages
    assert ("F", "Derive") in messages


def test_shipped_rule_base_is_valid(fixture_facts):
    rules = load_rule_files()
    assert validate(rules, KNOWN_FACTS, OFFERS, CHANNELS) == []
    outcomes = [run(rules, facts) for facts in fixture_facts.values()]
    assert any(o.allowed for o in outcomes)


@pytest.fixture
def fixture_facts(built):
    data = service.get_data()
    return build_facts(data.table, data.features, data.tables["interventions"])


def test_build_facts_from_fixtures(fixture_facts):
    assert len(fixture_facts) == 12
    facts = next(iter(fixture_facts.values()))
    assert set(facts) <= set(KNOWN_FACTS)
    assert {"trend_ratio", "churn_prob", "risk_band", "offers_last_90d"} <= set(facts)
    assert all(type(v) in (int, float, str, bool) for v in facts.values())


def test_trace_endpoint(client, login, built):
    staff = login("staff1")
    r = client.get("/api/rules/trace/M0001", headers=staff)
    assert r.status_code == 200
    body = r.json()
    assert body["member_id"] == "M0001" and {"firings", "allowed", "blocked"} <= set(body)
    assert client.get("/api/rules/trace/NOPE", headers=staff).status_code == 404
    assert client.get("/api/rules", headers=staff).status_code == 403
    rules = client.get("/api/rules", headers=login("admin")).json()
    assert rules["rules"] and rules["issues"] == []


def test_glossary_names_every_rule_and_offer(client, login):
    body = client.get("/api/rules/glossary", headers=login("staff1")).json()
    assert set(body["offers"]) == set(OFFERS)
    assert all(rule.id in body["rules"] for rule in load_rule_files())
    assert body["facts"]["trend_ratio"] and "routine_disrupted" in body["facts"]


def test_guardrail_check_reports_blocks(client, login, built):
    manager = login("manager")

    def post(items, headers=manager):
        return client.post("/api/rules/check", json={"items": items}, headers=headers)

    items = [
        {"member_id": "M0008", "offer_id": "free_pt_session", "channel": "call"},
        {"member_id": "M0007", "offer_id": "discount_1m", "channel": "email"},
        {"member_id": "M0007", "offer_id": "class_pass", "channel": "sms"},
        {"member_id": "M0005", "offer_id": "checkin_message", "channel": "sms"},
    ]
    ok, discount, off_playbook, fatigued = post(items).json()
    assert ok["allowed"] and ok["on_playbook"] and ok["violations"] == []
    assert not discount["allowed"]
    assert discount["violations"][0]["rule_id"] == "G03_discount_eligibility"
    assert off_playbook["allowed"] and not off_playbook["on_playbook"]
    assert fatigued["violations"][0]["blocks"] == "all"
    assert fatigued["violations"][0]["rule_id"] == "G01_contact_fatigue"

    unknown_member = [{"member_id": "NOPE", "offer_id": "class_pass", "channel": "sms"}]
    unknown_offer = [{"member_id": "M0001", "offer_id": "nope", "channel": "sms"}]
    assert post(unknown_member).status_code == 404
    assert post(unknown_offer).status_code == 422
    assert post(items, login("staff1")).status_code == 403

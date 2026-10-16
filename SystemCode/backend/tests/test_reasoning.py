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
    assert not parse_condition("churn_prob >= 0.5").holds({"churn_prob": "high"})
    for bad in ["__import__('os') == 1", "x >= ", "a ~ 1", "a in 3", "a == [1]"]:
        with pytest.raises(ValueError):
            parse_condition(bad)
    with pytest.raises(ValidationError):
        load_rules(
            "- {id: x, kind: derive, description: d, when: [a > 1], then: {block: all}, source: s}"
        )


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
"""
    )
    messages = {
        (i.rule_id, i.message.split(" ")[0]) for i in validate(rules, KNOWN_FACTS, OFFERS, CHANNELS)
    }
    assert ("A", "Contradicts") in messages and ("D", "Contradicts") not in messages
    assert {("C", "Unknown"), ("C", "Unreachable:")} <= messages


def test_rule_files_load(fixture_facts):
    rules = load_rule_files()
    assert rules
    for facts in fixture_facts.values():
        run(rules, facts)


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
    rules = client.get("/api/rules", headers=staff).json()
    assert rules["rules"] and "issues" in rules

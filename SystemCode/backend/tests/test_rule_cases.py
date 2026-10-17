import pytest
import yaml

from anchorai.catalog import Constraints
from anchorai.discovery import service
from anchorai.reasoning.engine import load_rule_files, run
from anchorai.reasoning.facts import build_facts
from tests.conftest import FIXTURES

SPEC = yaml.safe_load((FIXTURES / "rule_cases.yaml").read_text())
RULES = load_rule_files()


def member_facts(case: dict) -> dict:
    base = {k: v for k, v in SPEC["base"].items() if k not in SPEC.get("base_drop", [])}
    facts = {**base, **case.get("facts", {})}
    for key in case.get("drop", []):
        facts.pop(key, None)
    return facts


@pytest.mark.parametrize("case", SPEC["cases"], ids=lambda c: c["id"])
def test_rule_case(case):
    expect = case["expect"]
    out = run(RULES, member_facts(case), case["id"])
    fired = {f.rule_id for f in out.firings}
    assert set(expect.get("fires", [])) <= fired
    assert not set(expect.get("silent", [])) & fired
    assert [p.offer_id for p in out.allowed] == expect["allowed"]
    if "blocked" in expect:
        assert out.blocked == expect["blocked"]


def test_caps_follow_settings(built):
    data = service.get_data()
    args = (data.table, data.features, data.tables["interventions"])
    default = build_facts(*args)
    loose = build_facts(
        *args,
        caps=Constraints(
            default_budget=0,
            default_staff_minutes=0,
            max_contacts_per_member_per_30d=5,
            max_offers_per_member_per_90d=5,
        ),
    )
    assert any(f["at_contact_cap"] for f in default.values())
    assert not any(f["at_contact_cap"] or f["at_offer_cap"] for f in loose.values())

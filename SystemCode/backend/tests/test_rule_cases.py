import pytest
import yaml

from anchorai.reasoning.engine import load_rule_files, run
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

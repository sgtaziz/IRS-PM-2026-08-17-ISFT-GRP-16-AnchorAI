"""Forward-chaining rule engine: match, resolve conflicts, fire, repeat until quiescent."""

from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from anchorai.reasoning.models import Proposal, Rule, RuleOutcome
from anchorai.schemas import RuleFiring

RULES_DIR = Path(__file__).parent / "rules"


def load_rules(yaml_text: str) -> list[Rule]:
    data = yaml.safe_load(yaml_text) or []
    if not isinstance(data, list):
        raise TypeError("A rule file must be a YAML list of rules")
    rules = [Rule.model_validate(r) for r in data]
    duplicates = sorted(i for i, n in Counter(r.id for r in rules).items() if n > 1)
    if duplicates:
        raise ValueError(f"Duplicate rule ids: {', '.join(duplicates)}")
    return rules


def rule_files_text(directory: Path = RULES_DIR) -> str:
    return "\n".join(p.read_text() for p in sorted(directory.glob("*.yaml")))


def load_rule_files(directory: Path = RULES_DIR) -> list[Rule]:
    return load_rules(rule_files_text(directory))


def _priority(rule: Rule, position: int) -> tuple[int, int, int]:
    # Salience first, then specificity (more conditions wins), then file order.
    return (rule.salience, len(rule.conditions), -position)


def _fire(
    rule: Rule,
    memory: dict[str, Any],
    proposals: list[Proposal],
    blocked: dict[str, str],
) -> str:
    then = rule.then
    if then.assert_ is not None:
        # First assertion wins: rules fire in priority order, so a fact is set by the
        # highest-priority rule that derives it and never changes after something read it.
        new = {k: v for k, v in then.assert_.items() if k not in memory}
        memory.update(new)
        kept = sorted(set(then.assert_) - set(new))
        effect = "assert " + ", ".join(f"{k}={v}" for k, v in new.items()) if new else "assert"
        return effect + (f" (kept existing {', '.join(kept)})" if kept else "")
    if then.propose is not None:
        proposals.append(then.propose.model_copy(update={"rule_id": rule.id}))
        return f"propose {then.propose.offer_id} via {then.propose.channel}"
    targets = ["all"] if then.block == "all" else then.block
    for target in targets:
        blocked.setdefault(target, rule.id)
    return "block " + ", ".join(targets)


def run(rules: Iterable[Rule], facts: dict[str, Any], member_id: str = "") -> RuleOutcome:
    active = [(i, r) for i, r in enumerate(rules) if r.enabled]
    memory = dict(facts)
    fired: set[str] = set()
    firings: list[RuleFiring] = []
    proposals: list[Proposal] = []
    blocked: dict[str, str] = {}

    while True:
        agenda = [
            (i, r)
            for i, r in active
            if r.id not in fired and all(c.holds(memory) for c in r.conditions)
        ]
        if not agenda:
            break
        _, rule = max(agenda, key=lambda item: _priority(item[1], item[0]))
        # Refraction: a rule fires at most once per run, which also guarantees termination.
        fired.add(rule.id)
        matched = {c.fact: memory[c.fact] for c in rule.conditions}
        effect = _fire(rule, memory, proposals, blocked)
        firings.append(
            RuleFiring(
                rule_id=rule.id,
                description=rule.description,
                facts_matched=matched,
                effect=effect,
            )
        )

    allowed: list[Proposal] = []
    if "all" not in blocked:
        seen: set[str] = set()
        for p in proposals:
            if p.offer_id not in blocked and p.offer_id not in seen:
                seen.add(p.offer_id)
                allowed.append(p)

    return RuleOutcome(
        member_id=member_id,
        facts=memory,
        firings=firings,
        proposals=proposals,
        blocked=blocked,
        allowed=allowed,
    )


def run_many(
    rules: list[Rule], facts_by_member: dict[str, dict[str, Any]]
) -> dict[str, RuleOutcome]:
    return {m: run(rules, facts, m) for m, facts in facts_by_member.items()}

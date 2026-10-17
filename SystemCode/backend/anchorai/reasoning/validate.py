"""Static checks on a rule base: the things a rule author can get wrong."""

import math
from collections import Counter
from collections.abc import Collection, Iterable, Mapping
from itertools import combinations
from typing import Literal

from pydantic import BaseModel

from anchorai.reasoning.conditions import Condition
from anchorai.reasoning.facts import FactSpec, value_type
from anchorai.reasoning.models import Rule


class Issue(BaseModel):
    rule_id: str
    severity: Literal["error", "warning"]
    message: str


def _satisfiable(conditions: list[Condition]) -> bool:
    """Whether some single value of one fact can meet all the conditions on it."""
    probe = [Condition("x", c.op, c.value) for c in conditions]
    candidates: set | None = None
    for c in conditions:
        if c.op in ("==", "in"):
            values = {c.value} if c.op == "==" else set(c.value)
            candidates = values if candidates is None else candidates & values
    if candidates is not None:
        return any(all(c.holds({"x": v}) for c in probe) for v in candidates)

    lo, lo_strict, hi, hi_strict = -math.inf, False, math.inf, False
    for c in conditions:
        if c.op in (">", ">=") and (c.value > lo or (c.value == lo and c.op == ">")):
            lo, lo_strict = c.value, c.op == ">"
        elif c.op in ("<", "<=") and (c.value < hi or (c.value == hi and c.op == "<")):
            hi, hi_strict = c.value, c.op == "<"
    if lo < hi:
        return True
    # A single point is left; only != / not in can still rule it out.
    return lo == hi and not lo_strict and not hi_strict and all(c.holds({"x": lo}) for c in probe)


def _can_both_hold(a: Rule, b: Rule) -> bool:
    by_fact: dict[str, list[Condition]] = {}
    for c in a.conditions + b.conditions:
        by_fact.setdefault(c.fact, []).append(c)
    return all(_satisfiable(cs) for cs in by_fact.values())


def _values(c: Condition) -> tuple:
    return c.value if c.op in ("in", "not in") else (c.value,)


def _condition_problems(
    rule: Rule, specs: Mapping[str, FactSpec], categories: Mapping[str, Collection[str]]
) -> list[Issue]:
    problems = []
    for c in rule.conditions:
        spec = specs.get(c.fact)
        if spec is None:
            continue
        wrong = [v for v in _values(c) if value_type(v) != spec.type]
        if wrong:
            problems.append(
                Issue(
                    rule_id=rule.id,
                    severity="error",
                    message=f"{c} never matches: '{c.fact}' is a {spec.type} fact",
                )
            )
        elif spec.type == "category" and c.fact in categories:
            unknown = [v for v in _values(c) if v not in categories[c.fact]]
            if unknown and c.op in ("==", "in") and len(unknown) == len(_values(c)):
                problems.append(
                    Issue(
                        rule_id=rule.id,
                        severity="warning",
                        message=f"{c} never matches: unknown {c.fact} {unknown}",
                    )
                )
    by_fact: dict[str, list[Condition]] = {}
    for c in rule.conditions:
        by_fact.setdefault(c.fact, []).append(c)
    for fact, cs in by_fact.items():
        if len(cs) > 1 and not _satisfiable(cs):
            problems.append(
                Issue(
                    rule_id=rule.id,
                    severity="error",
                    message=f"Can never fire: its conditions on '{fact}' contradict each other",
                )
            )
    return problems


def _always_blocked(playbook: Rule, guardrail: Rule) -> bool:
    """Exact check only: every guardrail condition is also a condition of the playbook."""
    own = {(c.fact, c.op, c.value) for c in playbook.conditions}
    return all((c.fact, c.op, c.value) in own for c in guardrail.conditions)


def validate(
    rules: list[Rule],
    known_facts: Mapping[str, FactSpec],
    offer_ids: Iterable[str],
    channels: Iterable[str],
    offer_channels: Mapping[str, Collection[str]] | None = None,
    inactive_offers: Collection[str] = (),
    categories: Mapping[str, Collection[str]] | None = None,
) -> list[Issue]:
    """`offer_channels` and `inactive_offers` bring in the live catalogue when there is one."""
    issues: list[Issue] = []
    known, offers, channels = set(known_facts), set(offer_ids), set(channels)
    categories = {"risk_band": ["low", "medium", "high"], **(categories or {})}
    enabled = [r for r in rules if r.enabled]

    for rule_id, n in Counter(r.id for r in rules).items():
        if n > 1:
            issues.append(Issue(rule_id=rule_id, severity="error", message=f"Duplicate id ({n}x)"))

    # Disabled rules still count for "does this fact exist", so switching off a derive rule
    # does not turn the rules that read its fact into errors.
    asserted: dict[str, set] = {}
    live_asserted: dict[str, set] = {}
    for r in rules:
        for fact, value in (r.then.assert_ or {}).items():
            asserted.setdefault(fact, set()).add(value)
            if r.enabled:
                live_asserted.setdefault(fact, set()).add(value)
            if r.enabled and fact in known:
                issues.append(
                    Issue(
                        rule_id=r.id,
                        severity="error",
                        message=f"Derive rules cannot change the input fact '{fact}'",
                    )
                )

    for r in enabled:
        issues.extend(_condition_problems(r, known_facts, categories))
        for c in r.conditions:
            if c.fact not in known and c.fact not in asserted:
                issues.append(
                    Issue(rule_id=r.id, severity="error", message=f"Unknown fact '{c.fact}'")
                )
            elif c.fact not in known and c.fact not in live_asserted:
                issues.append(
                    Issue(
                        rule_id=r.id,
                        severity="warning",
                        message=f"Unreachable: '{c.fact}' is only asserted by disabled rules",
                    )
                )
            elif c.fact not in known and c.op in ("==", "in"):
                wanted = {c.value} if c.op == "==" else set(c.value)
                if not wanted & live_asserted[c.fact]:
                    issues.append(
                        Issue(
                            rule_id=r.id,
                            severity="warning",
                            message=f"Unreachable: no rule asserts {c}",
                        )
                    )
        if r.then.propose is not None:
            p = r.then.propose
            if p.offer_id not in offers:
                issues.append(
                    Issue(rule_id=r.id, severity="error", message=f"Unknown offer '{p.offer_id}'")
                )
            if p.channel not in channels:
                issues.append(
                    Issue(rule_id=r.id, severity="error", message=f"Unknown channel '{p.channel}'")
                )
            elif (
                offer_channels
                and p.offer_id in offer_channels
                and p.channel not in offer_channels[p.offer_id]
            ):
                issues.append(
                    Issue(
                        rule_id=r.id,
                        severity="error",
                        message=f"Catalogue does not offer '{p.offer_id}' by {p.channel}",
                    )
                )
            if p.offer_id in inactive_offers:
                issues.append(
                    Issue(
                        rule_id=r.id,
                        severity="warning",
                        message=f"Offer '{p.offer_id}' is inactive in the catalogue",
                    )
                )
        if isinstance(r.then.block, list):
            for offer_id in set(r.then.block) - offers:
                issues.append(
                    Issue(rule_id=r.id, severity="error", message=f"Unknown offer '{offer_id}'")
                )

    for playbook in (r for r in enabled if r.then.propose is not None):
        for guardrail in (r for r in enabled if r.then.block is not None):
            blocks = guardrail.then.block
            if (blocks == "all" or playbook.then.propose.offer_id in blocks) and _always_blocked(
                playbook, guardrail
            ):
                issues.append(
                    Issue(
                        rule_id=playbook.id,
                        severity="warning",
                        message=f"Always blocked by guardrail {guardrail.id}",
                    )
                )

    derives = [r for r in enabled if r.then.assert_]
    for a, b in combinations(derives, 2):
        clashes = [
            f for f, v in a.then.assert_.items() if f in b.then.assert_ and b.then.assert_[f] != v
        ]
        if clashes and _can_both_hold(a, b):
            issues.append(
                Issue(
                    rule_id=a.id,
                    severity="warning",
                    message=(
                        f"Contradicts {b.id} on {', '.join(clashes)} when both match; "
                        "whichever fires first sets the value and the other is ignored"
                    ),
                )
            )
    return issues

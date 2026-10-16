"""Static checks on a rule base: the things a rule author can get wrong."""

import math
from collections import Counter
from collections.abc import Iterable
from itertools import combinations
from typing import Literal

from pydantic import BaseModel

from anchorai.reasoning.conditions import Condition
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


def validate(
    rules: list[Rule],
    known_facts: Iterable[str],
    offer_ids: Iterable[str],
    channels: Iterable[str],
) -> list[Issue]:
    issues: list[Issue] = []
    known, offers, channels = set(known_facts), set(offer_ids), set(channels)
    enabled = [r for r in rules if r.enabled]

    for rule_id, n in Counter(r.id for r in rules).items():
        if n > 1:
            issues.append(Issue(rule_id=rule_id, severity="error", message=f"Duplicate id ({n}x)"))

    asserted: dict[str, set] = {}
    for r in enabled:
        for fact, value in (r.then.assert_ or {}).items():
            asserted.setdefault(fact, set()).add(value)
            if fact in known:
                issues.append(
                    Issue(
                        rule_id=r.id,
                        severity="error",
                        message=f"Derive rules cannot change the input fact '{fact}'",
                    )
                )

    for r in rules:
        for c in r.conditions:
            if c.fact not in known and c.fact not in asserted:
                issues.append(
                    Issue(rule_id=r.id, severity="error", message=f"Unknown fact '{c.fact}'")
                )
            elif c.fact not in known and c.op in ("==", "in"):
                wanted = {c.value} if c.op == "==" else set(c.value)
                if not wanted & asserted[c.fact]:
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
        if isinstance(r.then.block, list):
            for offer_id in set(r.then.block) - offers:
                issues.append(
                    Issue(rule_id=r.id, severity="error", message=f"Unknown offer '{offer_id}'")
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
                        "the higher-priority rule's value wins and the other is ignored"
                    ),
                )
            )
    return issues

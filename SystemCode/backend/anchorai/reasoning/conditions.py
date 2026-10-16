"""Rule conditions: `<fact> <op> <literal>`, parsed without eval."""

import operator
import re
from dataclasses import dataclass
from typing import Any

import yaml

_PATTERN = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s+(>=|<=|==|!=|>|<|not in|in)\s+(.+?)\s*$")
_COMPARE = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
}


@dataclass(frozen=True)
class Condition:
    fact: str
    op: str
    value: Any

    def holds(self, facts: dict[str, Any]) -> bool:
        if self.fact not in facts:
            return False
        actual = facts[self.fact]
        try:
            if self.op == "in":
                return actual in self.value
            if self.op == "not in":
                return actual not in self.value
            return bool(_COMPARE[self.op](actual, self.value))
        except TypeError:
            # e.g. comparing a string fact with a number: treat as not matched.
            return False

    def __str__(self) -> str:
        return f"{self.fact} {self.op} {self.value!r}"


def parse_condition(text: str) -> Condition:
    match = _PATTERN.match(text)
    if not match:
        raise ValueError(f"Cannot parse condition {text!r}; expected '<fact> <op> <value>'")
    fact, op, raw = match.groups()
    # YAML's safe loader gives numbers, booleans, quoted strings and [a, b] lists for free.
    try:
        value = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ValueError(f"Cannot parse value in condition {text!r}: {e}") from None
    if op in ("in", "not in") and not isinstance(value, list):
        raise ValueError(f"'{op}' needs a list value, e.g. [a, b], in {text!r}")
    if isinstance(value, dict | list) and op not in ("in", "not in"):
        raise ValueError(f"Only 'in' and 'not in' take a list value, in {text!r}")
    return Condition(fact, op, value)

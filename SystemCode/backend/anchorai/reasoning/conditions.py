"""Rule conditions: `<fact> <op> <literal>`, parsed without eval."""

import operator
import re
from dataclasses import dataclass

Scalar = bool | int | float | str

_PATTERN = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s+(>=|<=|==|!=|>|<|not in|in)\s+(.+?)\s*$")
_INT = re.compile(r"^-?\d+$")
_FLOAT = re.compile(r"^-?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$")
_BARE = re.compile(r"^[A-Za-z_][A-Za-z0-9_ \-]*$")
_COMPARE = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
}
NUMERIC_OPS = {">=", "<=", ">", "<"}


def _same_kind(a: Scalar, b: Scalar) -> bool:
    # Python treats True == 1; rules must not, so booleans only ever match booleans.
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool)
    return isinstance(a, int | float) == isinstance(b, int | float)


@dataclass(frozen=True)
class Condition:
    fact: str
    op: str
    value: Scalar | tuple[Scalar, ...]

    def holds(self, facts: dict[str, Scalar]) -> bool:
        """False when the fact is missing or of another kind, whatever the operator."""
        if self.fact not in facts:
            return False
        actual = facts[self.fact]
        if self.op in ("in", "not in"):
            found = any(_same_kind(actual, v) and actual == v for v in self.value)
            return found if self.op == "in" else not found
        if not _same_kind(actual, self.value):
            return False
        return bool(_COMPARE[self.op](actual, self.value))

    def __str__(self) -> str:
        return f"{self.fact} {self.op} {self.value!r}"


def parse_scalar(raw: str) -> Scalar:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        return raw[1:-1]
    if raw in ("true", "false"):
        return raw == "true"
    if _INT.match(raw):
        return int(raw)
    if _FLOAT.match(raw):
        return float(raw)
    if _BARE.match(raw):
        return raw
    raise ValueError(f"Cannot read value {raw!r}; quote strings with special characters")


def parse_condition(text: str) -> Condition:
    match = _PATTERN.match(text)
    if not match:
        raise ValueError(f"Cannot parse condition {text!r}; expected '<fact> <op> <value>'")
    fact, op, raw = match.groups()
    if op in ("in", "not in"):
        if not (raw.startswith("[") and raw.endswith("]")):
            raise ValueError(f"'{op}' needs a list value, e.g. [a, b], in {text!r}")
        items = [i for i in raw[1:-1].split(",") if i.strip()]
        if not items:
            raise ValueError(f"Empty list in {text!r}")
        return Condition(fact, op, tuple(parse_scalar(i) for i in items))
    value = parse_scalar(raw)
    if op in NUMERIC_OPS and (isinstance(value, bool) or not isinstance(value, int | float)):
        raise ValueError(f"'{op}' needs a number, in {text!r}")
    return Condition(fact, op, value)

from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StringConstraints,
    field_validator,
    model_validator,
)

from anchorai.reasoning.conditions import Condition, parse_condition
from anchorai.schemas import RuleFiring

RuleKind = Literal["derive", "playbook", "guardrail"]
RuleId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^[A-Za-z0-9_]+$")
]
Source = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Proposal(BaseModel):
    offer_id: str
    channel: str
    rule_id: str = ""


class Then(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True, extra="forbid")

    assert_: dict[str, bool | int | float | str] | None = Field(default=None, alias="assert")
    propose: Proposal | None = None
    block: Literal["all"] | list[str] | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "Then":
        if sum(x is not None for x in (self.assert_, self.propose, self.block)) != 1:
            raise ValueError("then: needs exactly one of assert, propose or block")
        if isinstance(self.block, list) and (not self.block or "all" in self.block):
            raise ValueError("block: needs offer ids, or the word all on its own")
        if self.assert_ is not None and not self.assert_:
            raise ValueError("assert: needs at least one fact")
        return self


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: RuleId
    kind: RuleKind
    salience: int = 0
    description: str
    when: list[str] = Field(min_length=1)
    then: Then
    source: Source
    enabled: bool = True

    _conditions: list[Condition] = PrivateAttr(default_factory=list)

    @field_validator("when")
    @classmethod
    def _parseable(cls, when: list[str]) -> list[str]:
        for text in when:
            parse_condition(text)
        return when

    @model_validator(mode="after")
    def _kind_matches_then(self) -> "Rule":
        expected = {"derive": "assert_", "playbook": "propose", "guardrail": "block"}[self.kind]
        if getattr(self.then, expected) is None:
            raise ValueError(f"{self.kind} rule {self.id} must use then: {expected.rstrip('_')}")
        self._conditions = [parse_condition(t) for t in self.when]
        return self

    @property
    def conditions(self) -> list[Condition]:
        return self._conditions


class RuleOutcome(BaseModel):
    """Result of running the rule base on one member: the C -> B contract."""

    member_id: str
    facts: dict[str, Any]
    firings: list[RuleFiring]
    proposals: list[Proposal]
    # offer_id (or "all") -> id of the guardrail that blocked it
    blocked: dict[str, str]
    allowed: list[Proposal]

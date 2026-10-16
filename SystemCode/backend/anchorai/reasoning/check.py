"""Live guardrail check for proposed contacts, e.g. a manager's plan override."""

from pydantic import BaseModel
from sqlmodel import Session

from anchorai import catalog
from anchorai.reasoning import service
from anchorai.reasoning.engine import run
from anchorai.reasoning.models import Rule
from anchorai.schemas import Channel


class ProposedItem(BaseModel):
    member_id: str
    offer_id: str
    channel: Channel


class Violation(BaseModel):
    rule_id: str
    description: str
    # The offer id the guardrail names, or "all".
    blocks: str


class ItemCheck(ProposedItem):
    allowed: bool
    violations: list[Violation]
    on_playbook: bool
    channel_offered: bool


class UnknownMember(LookupError):
    pass


class UnknownOffer(LookupError):
    pass


def check_items(session: Session, items: list[ProposedItem]) -> list[ItemCheck]:
    offers = {o.offer_id: o for o in catalog.list_offers(session)}
    facts = service.all_facts()
    for item in items:
        if item.member_id not in facts:
            raise UnknownMember(item.member_id)
        if item.offer_id not in offers:
            raise UnknownOffer(item.offer_id)

    _, rules = service.active_rules(session)
    by_id: dict[str, Rule] = {r.id: r for r in rules}
    outcomes = {m: run(rules, facts[m], m) for m in {i.member_id for i in items}}

    results = []
    for item in items:
        outcome = outcomes[item.member_id]
        violations = [
            Violation(rule_id=rule_id, description=by_id[rule_id].description, blocks=target)
            for target, rule_id in outcome.blocked.items()
            if target in ("all", item.offer_id)
        ]
        results.append(
            ItemCheck(
                **item.model_dump(),
                allowed=not violations,
                violations=violations,
                on_playbook=any(p.offer_id == item.offer_id for p in outcome.proposals),
                channel_offered=item.channel in offers[item.offer_id].channels,
            )
        )
    return results

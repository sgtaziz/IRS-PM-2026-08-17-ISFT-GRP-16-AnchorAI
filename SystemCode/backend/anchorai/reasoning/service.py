"""Rule base and traces for the API: active rule version from the DB, facts from Stream A."""

import threading
from typing import Any

import yaml
from pydantic import BaseModel
from sqlmodel import Session, select

from anchorai import catalog
from anchorai.db.models import RuleVersion
from anchorai.discovery import service as member_data
from anchorai.knowledge.signals import kg_facts_path, load_kg_facts
from anchorai.reasoning.engine import load_rule_files, load_rules, run
from anchorai.reasoning.facts import KNOWN_FACTS, build_facts
from anchorai.reasoning.models import Rule, RuleOutcome
from anchorai.reasoning.validate import Issue, validate
from anchorai.schemas import Channel


class RuleSet(BaseModel):
    version: int | None
    rules: list[Rule]
    issues: list[Issue]


class Glossary(BaseModel):
    """Readable names for the ids the UI shows: rules, offers and facts."""

    rules: dict[str, str]
    offers: dict[str, str]
    facts: dict[str, str]
    # offer_id -> channels its catalogue entry allows, for active offers only
    offer_channels: dict[str, list[str]]


class InvalidRuleBase(RuntimeError):
    pass


_lock = threading.Lock()
_facts: tuple[Any, dict[str, dict[str, Any]]] | None = None


def active_rules(session: Session) -> tuple[int | None, list[Rule]]:
    """The active DB rule version, or the rule files when the DB has none."""
    version = session.exec(
        select(RuleVersion).where(RuleVersion.is_active).order_by(RuleVersion.version.desc())
    ).first()
    if version is None:
        return None, load_rule_files()
    try:
        return version.version, load_rules(version.yaml_text)
    except (ValueError, TypeError, yaml.YAMLError) as e:
        raise InvalidRuleBase(f"Active rule version {version.version} is invalid: {e}") from e


def _segment_names() -> list[str]:
    try:
        return sorted(member_data.get_data().table["segment"].unique())
    except member_data.DataNotBuilt:
        return []


def check(session: Session, rules: list[Rule]) -> list[Issue]:
    offers = catalog.list_offers(session)
    segments = _segment_names()
    return validate(
        rules,
        KNOWN_FACTS,
        [o.offer_id for o in offers],
        [c.value for c in Channel],
        offer_channels={o.offer_id: [c.value for c in o.channels] for o in offers},
        inactive_offers={o.offer_id for o in offers if not o.active},
        categories={"segment": segments} if segments else None,
    )


def inactive_offers(session: Session) -> set[str]:
    return {o.offer_id for o in catalog.list_offers(session) if not o.active}


def drop_inactive(session: Session, outcome: RuleOutcome) -> RuleOutcome:
    inactive = inactive_offers(session)
    outcome.allowed = [p for p in outcome.allowed if p.offer_id not in inactive]
    return outcome


def rule_set(session: Session) -> RuleSet:
    version, rules = active_rules(session)
    return RuleSet(version=version, rules=rules, issues=check(session, rules))


def glossary(session: Session) -> Glossary:
    _, rules = active_rules(session)
    facts = {name: spec.description for name, spec in KNOWN_FACTS.items()}
    # Derived facts have no spec; the rule that asserts them describes them best.
    for r in rules:
        for name in r.then.assert_ or {}:
            facts.setdefault(name, r.description)
    return Glossary(
        rules={r.id: r.description for r in rules},
        offers={o.offer_id: o.name for o in catalog.list_offers(session)},
        facts=facts,
        offer_channels={
            o.offer_id: list(o.channels) for o in catalog.list_offers(session) if o.active
        },
    )


def all_facts(session: Session | None = None) -> dict[str, dict[str, Any]]:
    """Facts for every member, rebuilt when Stream A's data, the KG facts or the caps change.

    Without a session the caps are the catalogue defaults.
    """
    global _facts
    data = member_data.get_data()
    kg_path = kg_facts_path()
    caps = catalog.get_constraints(session) if session is not None else None
    key = (
        data.stamp,
        kg_path.stat().st_mtime if kg_path.exists() else None,
        tuple(caps.model_dump().items()) if caps else None,
    )
    with _lock:
        if _facts is None or _facts[0] != key:
            facts = build_facts(
                data.table, data.features, data.tables["interventions"], load_kg_facts(), caps
            )
            _facts = (key, facts)
        return _facts[1]


def trace(session: Session, member_id: str) -> RuleOutcome | None:
    facts = all_facts(session).get(member_id)
    if facts is None:
        return None
    _, rules = active_rules(session)
    return drop_inactive(session, run(rules, facts, member_id))

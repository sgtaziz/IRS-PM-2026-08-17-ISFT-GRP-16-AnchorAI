"""Editing the rule base: dry-run checks, draft tests, and versioned saves (W40)."""

from datetime import datetime
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from anchorai import catalog
from anchorai.db.audit import record_audit
from anchorai.db.models import RuleVersion, User
from anchorai.reasoning import service
from anchorai.reasoning.engine import run
from anchorai.reasoning.facts import KNOWN_FACTS, FactType
from anchorai.reasoning.models import Rule, RuleOutcome
from anchorai.reasoning.validate import Issue
from anchorai.schemas import Channel


class Report(BaseModel):
    rule_count: int
    parse_errors: list[str]
    issues: list[Issue]

    @property
    def ok(self) -> bool:
        return not self.parse_errors and all(i.severity != "error" for i in self.issues)


class VersionSummary(BaseModel):
    version: int
    note: str
    created_by: str | None
    created_at: datetime
    is_active: bool
    rule_count: int


class VersionDetail(VersionSummary):
    yaml_text: str


class FactInfo(BaseModel):
    name: str
    type: FactType
    description: str
    source: str
    derived: bool
    choices: list[str] = []


class OfferInfo(BaseModel):
    offer_id: str
    name: str
    channels: list[str]


class Vocabulary(BaseModel):
    facts: list[FactInfo]
    offers: list[OfferInfo]
    channels: list[str]


class InvalidDraft(ValueError):
    def __init__(self, report: Report):
        super().__init__("Rules are not valid")
        self.report = report


class UnknownVersion(LookupError):
    pass


class UnknownRule(LookupError):
    pass


class StaleRules(RuntimeError):
    pass


BAND_CHOICES = {"risk_band": ["low", "medium", "high"]}


def dump_rules(rules: list[Rule]) -> str:
    """YAML in the rule files' field names; `load_rules(dump_rules(r))` equals `r`."""
    entries = []
    for r in rules:
        entry: dict[str, Any] = {
            "id": r.id,
            "kind": r.kind,
            "salience": r.salience,
            "description": r.description,
            "when": list(r.when),
            "then": r.then.model_dump(mode="json", exclude_none=True, exclude={"propose"}),
            "source": r.source,
        }
        if r.then.propose is not None:
            entry["then"]["propose"] = {
                "offer_id": r.then.propose.offer_id,
                "channel": r.then.propose.channel,
            }
        if not r.enabled:
            entry["enabled"] = False
        entries.append(entry)
    return yaml.safe_dump(entries, sort_keys=False, allow_unicode=True, width=100)


def _loc(error: Any) -> str:
    loc = [str(p) for p in error["loc"] if p != "__root__"]
    return ".".join(loc)


def _parse(yaml_text: str) -> tuple[list[Rule], list[str]]:
    try:
        data = yaml.safe_load(yaml_text) or []
    except yaml.YAMLError as e:
        return [], [f"YAML: {' '.join(str(e).split())}"]
    if not isinstance(data, list):
        return [], ["A rule file must be a YAML list of rules"]
    rules: list[Rule] = []
    errors: list[str] = []
    for i, raw in enumerate(data, start=1):
        name = f"rule {raw['id']}" if isinstance(raw, dict) and "id" in raw else f"rule #{i}"
        try:
            rules.append(Rule.model_validate(raw))
        except ValidationError as e:
            for err in e.errors():
                where = _loc(err)
                msg = err["msg"].removeprefix("Value error, ")
                errors.append(f"{name}: {where + ': ' if where else ''}{msg}")
    return rules, errors


def check_draft(session: Session, yaml_text: str) -> tuple[list[Rule], Report]:
    rules, errors = _parse(yaml_text)
    issues = service.check(session, rules) if not errors else []
    return rules, Report(rule_count=len(rules), parse_errors=errors, issues=issues)


def run_draft(session: Session, yaml_text: str, member_id: str) -> RuleOutcome | None:
    rules, report = check_draft(session, yaml_text)
    if report.parse_errors:
        raise InvalidDraft(report)
    facts = service.all_facts().get(member_id)
    return None if facts is None else run(rules, facts, member_id)


def vocabulary(session: Session) -> Vocabulary:
    _, rules = service.active_rules(session)
    facts = [
        FactInfo(
            name=name,
            type=spec.type,
            description=spec.description,
            source=spec.source,
            derived=False,
            choices=BAND_CHOICES.get(name, []),
        )
        for name, spec in KNOWN_FACTS.items()
    ]
    derived: dict[str, FactInfo] = {}
    for r in rules:
        for name, value in (r.then.assert_ or {}).items():
            if name in KNOWN_FACTS:
                continue
            info = derived.setdefault(
                name,
                FactInfo(
                    name=name,
                    type="bool" if isinstance(value, bool) else "category",
                    description=r.description,
                    source=f"rule {r.id}",
                    derived=True,
                ),
            )
            if info.type == "category" and str(value) not in info.choices:
                info.choices.append(str(value))
    offers = [
        OfferInfo(offer_id=o.offer_id, name=o.name, channels=[c.value for c in o.channels])
        for o in catalog.list_offers(session)
    ]
    return Vocabulary(
        facts=facts + list(derived.values()), offers=offers, channels=[c.value for c in Channel]
    )


def _summary(v: RuleVersion, usernames: dict[int, str]) -> VersionSummary:
    return VersionSummary(
        version=v.version,
        note=v.note,
        created_by=usernames.get(v.created_by_id) if v.created_by_id else None,
        created_at=v.created_at,
        is_active=v.is_active,
        rule_count=_count(v.yaml_text),
    )


def _count(yaml_text: str) -> int:
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return 0
    return len(data) if isinstance(data, list) else 0


def _usernames(session: Session) -> dict[int, str]:
    return {u.id: u.username for u in session.exec(select(User)).all() if u.id is not None}


def list_versions(session: Session) -> list[VersionSummary]:
    names = _usernames(session)
    rows = session.exec(select(RuleVersion).order_by(RuleVersion.version.desc())).all()
    return [_summary(v, names) for v in rows]


def _get(session: Session, version: int) -> RuleVersion:
    row = session.exec(select(RuleVersion).where(RuleVersion.version == version)).first()
    if row is None:
        raise UnknownVersion(f"No rule version {version}")
    return row


def get_version(session: Session, version: int) -> VersionDetail:
    row = _get(session, version)
    return VersionDetail(**_summary(row, _usernames(session)).model_dump(), yaml_text=row.yaml_text)


def _diff(before: list[Rule], after: list[Rule]) -> dict[str, list[str]]:
    old, new = {r.id: r for r in before}, {r.id: r for r in after}
    return {
        "added": sorted(new.keys() - old.keys()),
        "removed": sorted(old.keys() - new.keys()),
        "changed": sorted(i for i in new.keys() & old.keys() if new[i] != old[i]),
    }


def _active_row(session: Session) -> RuleVersion | None:
    return session.exec(
        select(RuleVersion).where(RuleVersion.is_active).order_by(RuleVersion.version.desc())
    ).first()


def _require_base(session: Session, base_version: int | None) -> None:
    row = _active_row(session)
    if (row.version if row else None) != base_version:
        raise StaleRules("The rules changed since you opened them; reload and try again")


def _before(session: Session) -> tuple[int | None, list[Rule]]:
    """The active rules for the audit trail; a broken active version must not block a fix."""
    try:
        return service.active_rules(session)
    except service.InvalidRuleBase:
        row = _active_row(session)
        return (row.version if row else None), []


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError:
        # Another writer took the same version number first.
        session.rollback()
        raise StaleRules("The rules changed since you opened them; reload and try again") from None


def save_version(
    session: Session,
    user: User,
    yaml_text: str,
    note: str,
    base_version: int | None,
    action: str = "rule_version_create",
) -> VersionSummary:
    rules, report = check_draft(session, yaml_text)
    if not report.ok:
        raise InvalidDraft(report)
    _require_base(session, base_version)
    before_version, before = _before(session)
    latest = session.exec(select(func.max(RuleVersion.version))).one() or 0
    for row in session.exec(select(RuleVersion).where(RuleVersion.is_active)).all():
        row.is_active = False
        session.add(row)
    row = RuleVersion(
        version=latest + 1,
        yaml_text=dump_rules(rules),
        note=note,
        created_by_id=user.id,
        is_active=True,
    )
    session.add(row)
    record_audit(
        session,
        user,
        action,
        "rule_version",
        str(row.version),
        before={"active_version": before_version, "rule_count": len(before)},
        after={"version": row.version, "rule_count": len(rules), "note": note}
        | _diff(before, rules),
    )
    _commit(session)
    return _summary(row, _usernames(session))


def set_enabled(
    session: Session,
    user: User,
    rule_id: str,
    enabled: bool,
    note: str | None,
    base_version: int | None,
) -> VersionSummary:
    _require_base(session, base_version)
    try:
        _, rules = service.active_rules(session)
    except service.InvalidRuleBase as e:
        raise InvalidDraft(Report(rule_count=0, parse_errors=[str(e)], issues=[])) from None
    rules = [r.model_copy(deep=True) for r in rules]
    target = next((r for r in rules if r.id == rule_id), None)
    if target is None:
        raise UnknownRule(f"No rule {rule_id}")
    target.enabled = enabled
    default = f"{'Enabled' if enabled else 'Disabled'} {rule_id}"
    return save_version(
        session,
        user,
        dump_rules(rules),
        note or default,
        base_version,
        action="rule_enable" if enabled else "rule_disable",
    )


def activate_version(
    session: Session, user: User, version: int, base_version: int | None
) -> VersionSummary:
    row = _get(session, version)
    _require_base(session, base_version)
    if row.is_active:
        return _summary(row, _usernames(session))
    rules, report = check_draft(session, row.yaml_text)
    if not report.ok:
        raise InvalidDraft(report)
    active_version, active = _before(session)
    # Conditional on the version the caller saw, so a concurrent activation loses instead of winning silently.
    deactivated = session.exec(
        update(RuleVersion)
        .where(RuleVersion.is_active, RuleVersion.version == base_version)
        .values(is_active=False)
    ).rowcount
    if base_version is not None and deactivated != 1:
        session.rollback()
        raise StaleRules("The rules changed since you opened them; reload and try again")
    session.exec(update(RuleVersion).where(RuleVersion.version == version).values(is_active=True))
    if (
        session.exec(
            select(func.count()).select_from(RuleVersion).where(RuleVersion.is_active)
        ).one()
        != 1
    ):
        session.rollback()
        raise StaleRules("The rules changed since you opened them; reload and try again")
    session.refresh(row)
    record_audit(
        session,
        user,
        "rule_version_activate",
        "rule_version",
        str(version),
        before={"active_version": active_version, "rule_count": len(active)},
        after={"active_version": version, "rule_count": len(rules)} | _diff(active, rules),
    )
    _commit(session)
    return _summary(row, _usernames(session))

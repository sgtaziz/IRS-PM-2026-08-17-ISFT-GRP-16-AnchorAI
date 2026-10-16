from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from anchorai.api.deps import SessionDep, require_role
from anchorai.db.models import User
from anchorai.discovery.service import DataNotBuilt
from anchorai.reasoning import check as guardrails
from anchorai.reasoning import service, versions
from anchorai.reasoning.models import RuleOutcome
from anchorai.reasoning.service import Glossary, RuleSet
from anchorai.reasoning.versions import (
    InvalidDraft,
    Report,
    StaleRules,
    UnknownRule,
    UnknownVersion,
    VersionDetail,
    VersionSummary,
    Vocabulary,
)

router = APIRouter()
AdminDep = Depends(require_role("admin"))
Admin = Annotated[User, AdminDep]


class DraftIn(BaseModel):
    yaml_text: str


class DraftTestIn(DraftIn):
    member_id: str


class SaveIn(DraftIn):
    note: str = Field(min_length=1)
    base_version: int | None


class EnableIn(BaseModel):
    enabled: bool
    note: str | None = None
    base_version: int | None


class CheckIn(BaseModel):
    items: list[guardrails.ProposedItem] = Field(min_length=1, max_length=500)


class ActivateIn(BaseModel):
    base_version: int | None


def _invalid(e: InvalidDraft) -> HTTPException:
    return HTTPException(422, e.report.model_dump())


@router.get("", response_model=RuleSet, dependencies=[AdminDep])
def list_rules(session: SessionDep):
    try:
        return service.rule_set(session)
    except service.InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None


@router.put("", response_model=VersionSummary)
def save_rules(body: SaveIn, session: SessionDep, user: Admin):
    try:
        return versions.save_version(
            session, user, body.yaml_text, body.note.strip(), body.base_version
        )
    except InvalidDraft as e:
        raise _invalid(e) from None
    except StaleRules as e:
        raise HTTPException(409, str(e)) from None


@router.post(
    "/check",
    response_model=list[guardrails.ItemCheck],
    dependencies=[Depends(require_role("manager", "admin"))],
)
def check_items(body: CheckIn, session: SessionDep):
    try:
        return guardrails.check_items(session, body.items)
    except guardrails.UnknownMember as e:
        raise HTTPException(404, f"Unknown member {e}") from None
    except guardrails.UnknownOffer as e:
        raise HTTPException(422, f"Unknown offer {e}") from None
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    except service.InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None


@router.get("/glossary", response_model=Glossary)
def glossary(session: SessionDep):
    try:
        return service.glossary(session)
    except service.InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None


@router.get("/vocabulary", response_model=Vocabulary, dependencies=[AdminDep])
def vocabulary(session: SessionDep):
    try:
        return versions.vocabulary(session)
    except service.InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None


@router.post("/validate", response_model=Report, dependencies=[AdminDep])
def validate_draft(body: DraftIn, session: SessionDep):
    _, report = versions.check_draft(session, body.yaml_text)
    return report


@router.post("/test", response_model=RuleOutcome, dependencies=[AdminDep])
def test_draft(body: DraftTestIn, session: SessionDep):
    try:
        outcome = versions.run_draft(session, body.yaml_text, body.member_id)
    except InvalidDraft as e:
        raise _invalid(e) from None
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    if outcome is None:
        raise HTTPException(404, f"Unknown member {body.member_id}")
    return outcome


@router.get("/versions", response_model=list[VersionSummary], dependencies=[AdminDep])
def list_versions(session: SessionDep):
    return versions.list_versions(session)


@router.get("/versions/{version}", response_model=VersionDetail, dependencies=[AdminDep])
def get_version(version: int, session: SessionDep):
    try:
        return versions.get_version(session, version)
    except UnknownVersion as e:
        raise HTTPException(404, str(e)) from None


@router.post("/versions/{version}/activate", response_model=VersionSummary)
def activate_version(version: int, body: ActivateIn, session: SessionDep, user: Admin):
    try:
        return versions.activate_version(session, user, version, body.base_version)
    except UnknownVersion as e:
        raise HTTPException(404, str(e)) from None
    except InvalidDraft as e:
        raise _invalid(e) from None
    except StaleRules as e:
        raise HTTPException(409, str(e)) from None


@router.get("/trace/{member_id}", response_model=RuleOutcome)
def trace(member_id: str, session: SessionDep):
    try:
        outcome = service.trace(session, member_id)
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    except service.InvalidRuleBase as e:
        raise HTTPException(500, str(e)) from None
    if outcome is None:
        raise HTTPException(404, f"Unknown member {member_id}")
    return outcome


@router.patch("/{rule_id}", response_model=VersionSummary)
def set_rule_enabled(rule_id: str, body: EnableIn, session: SessionDep, user: Admin):
    try:
        return versions.set_enabled(
            session, user, rule_id, body.enabled, body.note, body.base_version
        )
    except UnknownRule as e:
        raise HTTPException(404, str(e)) from None
    except InvalidDraft as e:
        raise _invalid(e) from None
    except StaleRules as e:
        raise HTTPException(409, str(e)) from None

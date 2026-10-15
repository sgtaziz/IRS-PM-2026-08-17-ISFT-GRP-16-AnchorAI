from datetime import UTC, date, datetime
from typing import Any, Literal

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

Role = Literal["staff", "manager", "admin"]
ROLES: tuple[Role, ...] = ("staff", "manager", "admin")


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    role: str
    full_name: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=utcnow)


class Plan(SQLModel, table=True):
    __tablename__ = "plans"

    id: int | None = Field(default=None, primary_key=True)
    week_start: date
    status: str = "draft"
    request: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    total_cost: float = 0.0
    total_staff_minutes: int = 0
    expected_members_retained: float = 0.0
    created_by_id: int | None = Field(default=None, foreign_key="users.id")
    approved_by_id: int | None = Field(default=None, foreign_key="users.id")
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)


class PlanItem(SQLModel, table=True):
    __tablename__ = "plan_items"

    id: int | None = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="plans.id", index=True)
    member_id: str = Field(index=True)
    offer_id: str
    channel: str
    expected_value: float
    explanation_id: str
    explanation: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    override_reason: str | None = None
    removed: bool = False


class Assignment(SQLModel, table=True):
    __tablename__ = "assignments"

    id: int | None = Field(default=None, primary_key=True)
    plan_item_id: int = Field(foreign_key="plan_items.id", index=True)
    staff_user_id: int = Field(foreign_key="users.id", index=True)
    priority: int = 0
    assigned_at: datetime = Field(default_factory=utcnow)


class Outcome(SQLModel, table=True):
    __tablename__ = "outcomes"

    id: int | None = Field(default=None, primary_key=True)
    plan_item_id: int = Field(foreign_key="plan_items.id", index=True)
    member_id: str = Field(index=True)
    logged_by_id: int = Field(foreign_key="users.id")
    outcome: str
    note: str | None = None
    logged_at: datetime = Field(default_factory=utcnow)


class RuleVersion(SQLModel, table=True):
    __tablename__ = "rule_versions"

    id: int | None = Field(default=None, primary_key=True)
    version: int = Field(unique=True)
    yaml_text: str
    note: str = ""
    created_by_id: int | None = Field(default=None, foreign_key="users.id")
    is_active: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=utcnow, index=True)
    user_id: int | None = Field(default=None, foreign_key="users.id")
    # Kept alongside user_id so entries stay readable after a user is deleted.
    username: str
    action: str = Field(index=True)
    entity: str
    entity_id: str | None = None
    before: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    after: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))


class AssistantFeedback(SQLModel, table=True):
    __tablename__ = "assistant_feedback"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    ts: datetime = Field(default_factory=utcnow)
    message: str
    answer: str
    intent: str | None = None
    tool: str | None = None
    rating: int
    comment: str | None = None

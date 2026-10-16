"""add gym entity overlay tables

Revision ID: 4daa708cd6c6
Revises: 842514595326
Create Date: 2026-10-16 13:50:31.795960

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "4daa708cd6c6"
down_revision: str | None = "842514595326"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "class_instructor_overrides",
        sa.Column("class_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("instructor_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("class_id"),
    )
    op.create_table(
        "gym_classes",
        sa.Column("class_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("club_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("instructor_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("class_id"),
    )
    op.create_table(
        "gym_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("entity_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("suppresses", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("gym_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_gym_events_entity_id"), ["entity_id"], unique=False)

    op.create_table(
        "gym_instructors",
        sa.Column("instructor_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("club_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("instructor_id"),
    )


def downgrade() -> None:
    op.drop_table("gym_instructors")
    with op.batch_alter_table("gym_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_gym_events_entity_id"))

    op.drop_table("gym_events")
    op.drop_table("gym_classes")
    op.drop_table("class_instructor_overrides")

"""add offer catalog, staff profiles and app settings

Revision ID: 842514595326
Revises: f776eaa9c4f3
Create Date: 2026-10-16 01:39:18.282872

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "842514595326"
down_revision: str | None = "f776eaa9c4f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "offer_catalog",
        sa.Column("offer_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("staff_minutes", sa.Integer(), nullable=False),
        sa.Column("inventory", sa.Integer(), nullable=True),
        sa.Column("channels", sa.JSON(), nullable=False),
        sa.Column("eligibility", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("required_skill", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("offer_id"),
    )
    op.create_table(
        "staff_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("weekly_hours", sa.Float(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("staff_profiles")
    op.drop_table("offer_catalog")
    op.drop_table("app_settings")

"""add user token version

Revision ID: ae1bdf6639aa
Revises: 4daa708cd6c6
Create Date: 2026-10-17 10:41:03.406245

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ae1bdf6639aa"
down_revision: str | None = "4daa708cd6c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("token_version")

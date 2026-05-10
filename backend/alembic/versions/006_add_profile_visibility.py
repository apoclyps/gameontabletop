"""add profile visibility flags

Revision ID: 006
Revises: 005
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("profile_public", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
    )
    op.add_column(
        "users",
        sa.Column("stats_public", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
    )


def downgrade() -> None:
    op.drop_column("users", "stats_public")
    op.drop_column("users", "profile_public")

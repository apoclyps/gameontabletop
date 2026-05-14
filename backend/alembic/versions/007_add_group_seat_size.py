"""add seat_size to groups

Revision ID: 007
Revises: 006
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("groups", sa.Column("seat_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("groups", "seat_size")

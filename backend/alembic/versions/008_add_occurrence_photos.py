"""add occurrence photos

Revision ID: 008
Revises: 007
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "occurrence_photos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "occurrence_id",
            UUID(as_uuid=True),
            sa.ForeignKey("night_occurrences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("photo_url", sa.String(1000), nullable=False),
        sa.Column("caption", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_occurrence_photos_occurrence_id",
        "occurrence_photos",
        ["occurrence_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_occurrence_photos_occurrence_id", table_name="occurrence_photos")
    op.drop_table("occurrence_photos")

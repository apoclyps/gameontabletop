"""create collection and friends tables

Revision ID: 004
Revises: 003
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_game_collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bgg_game_id", sa.Integer(), nullable=True),
        sa.Column("game_title", sa.String(300), nullable=False),
        sa.Column("game_thumbnail_url", sa.String(500), nullable=True),
        sa.Column("min_players", sa.Integer(), nullable=True),
        sa.Column("max_players", sa.Integer(), nullable=True),
        sa.Column("complexity", sa.Numeric(3, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="own"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("acquired_at", sa.Date(), nullable=True),
        sa.Column(
            "collection_visible_to",
            sa.String(20),
            nullable=False,
            server_default="friends",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "bgg_game_id", name="uq_user_bgg_game"),
    )
    op.create_index(
        "ix_user_game_collections_user_id_status",
        "user_game_collections",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_user_game_collections_bgg_game_id",
        "user_game_collections",
        ["bgg_game_id"],
        unique=False,
    )

    op.create_table(
        "user_friendships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("addressee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["addressee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
        sa.CheckConstraint(
            "requester_id != addressee_id", name="ck_no_self_friendship"
        ),
    )
    op.create_index(
        "ix_user_friendships_addressee_id_status",
        "user_friendships",
        ["addressee_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_friendships_addressee_id_status", table_name="user_friendships"
    )
    op.drop_table("user_friendships")
    op.drop_index(
        "ix_user_game_collections_bgg_game_id", table_name="user_game_collections"
    )
    op.drop_index(
        "ix_user_game_collections_user_id_status", table_name="user_game_collections"
    )
    op.drop_table("user_game_collections")

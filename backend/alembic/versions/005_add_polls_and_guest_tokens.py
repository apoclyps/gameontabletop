"""add polls and guest tokens

Revision ID: 005
Revises: 004
Create Date: 2026-05-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guest_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("guest_name", sa.String(100), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurrence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["night_series.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["occurrence_id"], ["night_occurrences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guest_tokens_token"), "guest_tokens", ["token"], unique=True)

    # Add guest_token_id and guest_name to rsvps now that guest_tokens exists
    op.add_column("rsvps", sa.Column("guest_token_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("rsvps", sa.Column("guest_name", sa.String(100), nullable=True))
    op.create_foreign_key(
        "fk_rsvps_guest_token",
        "rsvps", "guest_tokens",
        ["guest_token_id"], ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "availability_polls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("chosen_option_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["night_series.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "poll_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposed_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("display_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["poll_id"], ["availability_polls.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add the circular FK now that poll_options exists
    op.create_foreign_key(
        "fk_polls_chosen_option",
        "availability_polls", "poll_options",
        ["chosen_option_id"], ["id"],
        ondelete="SET NULL",
    )

    # Add poll_id FK to guest_tokens now that availability_polls exists
    op.create_foreign_key(
        "fk_guest_tokens_poll",
        "guest_tokens", "availability_polls",
        ["poll_id"], ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "poll_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("option_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("guest_token_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("guest_name", sa.String(100), nullable=True),
        sa.Column("response", sa.String(10), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["poll_id"], ["availability_polls.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["option_id"], ["poll_options.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guest_token_id"], ["guest_tokens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("poll_responses")
    op.drop_constraint("fk_guest_tokens_poll", "guest_tokens", type_="foreignkey")
    op.drop_constraint("fk_polls_chosen_option", "availability_polls", type_="foreignkey")
    op.drop_table("poll_options")
    op.drop_table("availability_polls")
    op.drop_constraint("fk_rsvps_guest_token", "rsvps", type_="foreignkey")
    op.drop_column("rsvps", "guest_token_id")
    op.drop_column("rsvps", "guest_name")
    op.drop_index(op.f("ix_guest_tokens_token"), table_name="guest_tokens")
    op.drop_table("guest_tokens")

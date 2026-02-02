"""reactions, view events, notifications

Revision ID: b7f2c1d4e5a6
Revises: 9c2d7a1e4f00
Create Date: 2026-02-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7f2c1d4e5a6"
down_revision = "9c2d7a1e4f00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reactions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("actor_address", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("actor_address", "target_type", "target_id", "kind", name="uq_reactions_actor_target_kind"),
    )
    op.create_index("ix_reactions_target_kind_created", "reactions", ["target_type", "target_id", "kind", "created_at"])
    op.create_index("ix_reactions_actor_created", "reactions", ["actor_address", "created_at"])

    op.create_table(
        "view_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("viewer_address", sa.String(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("viewer_address", "target_type", "target_id", "window_start", name="uq_views_viewer_target_window"),
    )
    op.create_index("ix_views_target_created", "view_events", ["target_type", "target_id", "created_at"])
    op.create_index("ix_views_target_window", "view_events", ["target_type", "target_id", "window_start"])
    op.create_index("ix_views_viewer_address", "view_events", ["viewer_address"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("recipient_address", sa.String(), nullable=False),
        sa.Column("actor_address", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        ["recipient_address", "read_at", "created_at"],
    )
    op.create_index("ix_notifications_target", "notifications", ["target_type", "target_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_target", table_name="notifications")
    op.drop_index("ix_notifications_recipient_read_created", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_views_viewer_address", table_name="view_events")
    op.drop_index("ix_views_target_window", table_name="view_events")
    op.drop_index("ix_views_target_created", table_name="view_events")
    op.drop_table("view_events")

    op.drop_index("ix_reactions_actor_created", table_name="reactions")
    op.drop_index("ix_reactions_target_kind_created", table_name="reactions")
    op.drop_table("reactions")


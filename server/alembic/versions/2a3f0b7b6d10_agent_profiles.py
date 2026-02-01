"""agent profiles

Revision ID: 2a3f0b7b6d10
Revises: 1c4f9e2f0c2b
Create Date: 2026-01-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2a3f0b7b6d10"
down_revision: Union[str, None] = "1c4f9e2f0c2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_profiles",
        sa.Column("address", sa.String(), primary_key=True),
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("avatar_mode", sa.String(), nullable=False, server_default="manual"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_profiles_nickname", "agent_profiles", ["nickname"])


def downgrade() -> None:
    op.drop_index("ix_agent_profiles_nickname", table_name="agent_profiles")
    op.drop_table("agent_profiles")


"""agent profile participant_type

Revision ID: 6b0b7d1d2e31
Revises: f1d0e7a4c2bd
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6b0b7d1d2e31"
down_revision: Union[str, None] = "f1d0e7a4c2bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_profiles",
        sa.Column("participant_type", sa.String(), nullable=False, server_default="unknown"),
    )
    # keep server_default for backfill; app can treat it as default.


def downgrade() -> None:
    op.drop_column("agent_profiles", "participant_type")


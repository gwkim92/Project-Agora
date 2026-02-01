"""add final vote window

Revision ID: 22d00a28e1a1
Revises: e4a6bba2f9db
Create Date: 2026-01-17 17:05:54.615427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22d00a28e1a1'
down_revision: Union[str, None] = 'e4a6bba2f9db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("final_vote_starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("final_vote_ends_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "final_vote_ends_at")
    op.drop_column("jobs", "final_vote_starts_at")

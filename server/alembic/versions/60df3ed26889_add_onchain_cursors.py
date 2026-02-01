"""add onchain cursors

Revision ID: 60df3ed26889
Revises: eeb49f137b5b
Create Date: 2026-01-17 16:03:12.155041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60df3ed26889'
down_revision: Union[str, None] = 'eeb49f137b5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "onchain_cursors",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("last_block", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("onchain_cursors")

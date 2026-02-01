"""admin access challenges (step-up signature)

Revision ID: 8b1a4c9d2e11
Revises: f1d0e7a4c2bd
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b1a4c9d2e11"
down_revision: Union[str, None] = "f1d0e7a4c2bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_access_challenges",
        sa.Column("address", sa.String(), primary_key=True),
        sa.Column("nonce", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("admin_access_challenges")


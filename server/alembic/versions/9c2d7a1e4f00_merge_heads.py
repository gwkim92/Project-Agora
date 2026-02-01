"""merge heads

Revision ID: 9c2d7a1e4f00
Revises: 6b0b7d1d2e31, 8b1a4c9d2e11
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op


revision: str = "9c2d7a1e4f00"
down_revision: Union[str, Sequence[str], None] = ("6b0b7d1d2e31", "8b1a4c9d2e11")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge revision (no-op).
    pass


def downgrade() -> None:
    # Merge revision (no-op).
    pass


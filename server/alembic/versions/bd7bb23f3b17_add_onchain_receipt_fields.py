"""add onchain receipt fields

Revision ID: bd7bb23f3b17
Revises: 8787adc26bec
Create Date: 2026-01-17 15:40:59.789336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd7bb23f3b17'
down_revision: Union[str, None] = '8787adc26bec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("close_tx_hash", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("close_chain_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("close_contract_address", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("close_block_number", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("close_log_index", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "close_log_index")
    op.drop_column("jobs", "close_block_number")
    op.drop_column("jobs", "close_contract_address")
    op.drop_column("jobs", "close_chain_id")
    op.drop_column("jobs", "close_tx_hash")

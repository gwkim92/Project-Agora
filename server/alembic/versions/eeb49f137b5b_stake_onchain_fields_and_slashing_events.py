"""stake onchain fields and slashing events

Revision ID: eeb49f137b5b
Revises: bd7bb23f3b17
Create Date: 2026-01-17 15:53:33.612138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eeb49f137b5b'
down_revision: Union[str, None] = 'bd7bb23f3b17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stakes", sa.Column("stake_tx_hash", sa.String(), nullable=True))
    op.add_column("stakes", sa.Column("stake_chain_id", sa.Integer(), nullable=True))
    op.add_column("stakes", sa.Column("stake_contract_address", sa.String(), nullable=True))
    op.add_column("stakes", sa.Column("stake_block_number", sa.Integer(), nullable=True))
    op.add_column("stakes", sa.Column("stake_log_index", sa.Integer(), nullable=True))

    op.create_table(
        "slashing_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("agent_address", sa.String(), nullable=False),
        sa.Column("amount_usdc", sa.Float(), nullable=False),
        sa.Column("recipient_address", sa.String(), nullable=True),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("tx_hash", sa.String(), nullable=True),
        sa.Column("chain_id", sa.Integer(), nullable=True),
        sa.Column("contract_address", sa.String(), nullable=True),
        sa.Column("block_number", sa.Integer(), nullable=True),
        sa.Column("log_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_slashing_events_agent_address", "slashing_events", ["agent_address"])
    op.create_index("ix_slashing_events_job_id", "slashing_events", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_slashing_events_job_id", table_name="slashing_events")
    op.drop_index("ix_slashing_events_agent_address", table_name="slashing_events")
    op.drop_table("slashing_events")

    op.drop_column("stakes", "stake_log_index")
    op.drop_column("stakes", "stake_block_number")
    op.drop_column("stakes", "stake_contract_address")
    op.drop_column("stakes", "stake_chain_id")
    op.drop_column("stakes", "stake_tx_hash")

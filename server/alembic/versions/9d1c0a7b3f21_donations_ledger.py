"""donations ledger (treasury events)

Revision ID: 9d1c0a7b3f21
Revises: 2a3f0b7b6d10
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d1c0a7b3f21"
down_revision: Union[str, None] = "2a3f0b7b6d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "donation_events",
        sa.Column("id", sa.String(), primary_key=True),  # chain:tx:logIndex
        sa.Column("donor_address", sa.String(), nullable=False),
        sa.Column("asset_address", sa.String(), nullable=False),
        sa.Column("amount_raw", sa.BigInteger(), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=True),
        sa.Column("purpose_id", sa.Integer(), nullable=True),
        sa.Column("memo_hash", sa.String(), nullable=True),
        sa.Column("tx_hash", sa.String(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("contract_address", sa.String(), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_donation_events_donor_address", "donation_events", ["donor_address"])
    op.create_index("ix_donation_events_asset_address", "donation_events", ["asset_address"])
    op.create_index("ix_donation_events_chain_id", "donation_events", ["chain_id"])
    op.create_index("ix_donation_events_created_at", "donation_events", ["created_at"])

    op.create_table(
        "donor_totals",
        sa.Column("donor_address", sa.String(), primary_key=True),
        sa.Column("total_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("first_event_id", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("donor_totals")

    op.drop_index("ix_donation_events_created_at", table_name="donation_events")
    op.drop_index("ix_donation_events_chain_id", table_name="donation_events")
    op.drop_index("ix_donation_events_asset_address", table_name="donation_events")
    op.drop_index("ix_donation_events_donor_address", table_name="donation_events")
    op.drop_table("donation_events")


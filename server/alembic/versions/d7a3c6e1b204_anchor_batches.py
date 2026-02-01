"""anchor batches (offchain snapshot anchoring)

Revision ID: d7a3c6e1b204
Revises: 9d1c0a7b3f21
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7a3c6e1b204"
down_revision: Union[str, None] = "9d1c0a7b3f21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anchor_batches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("salt", sa.String(), nullable=False),
        sa.Column("anchor_root", sa.String(), nullable=False),
        sa.Column("anchor_uri", sa.String(), nullable=False),
        sa.Column("anchor_tx_hash", sa.String(), nullable=True),
        sa.Column("anchor_chain_id", sa.Integer(), nullable=True),
        sa.Column("anchor_contract_address", sa.String(), nullable=True),
        sa.Column("anchor_block_number", sa.Integer(), nullable=True),
        sa.Column("anchor_log_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("job_id", name="uq_anchor_batches_job_id"),
    )
    op.create_index("ix_anchor_batches_job_id", "anchor_batches", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_anchor_batches_job_id", table_name="anchor_batches")
    op.drop_table("anchor_batches")


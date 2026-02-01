"""agr ledger and job boosts

Revision ID: 4cadb52f32dc
Revises: 22d00a28e1a1
Create Date: 2026-01-17 17:55:43.463015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cadb52f32dc'
down_revision: Union[str, None] = '22d00a28e1a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("featured_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("featured_score", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "agr_ledger",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agr_ledger_address", "agr_ledger", ["address"])
    op.create_index("ix_agr_ledger_job_id", "agr_ledger", ["job_id"])

    op.create_table(
        "job_boosts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("amount_agr", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("featured_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_job_boosts_job_id", "job_boosts", ["job_id"])
    op.create_index("ix_job_boosts_address", "job_boosts", ["address"])


def downgrade() -> None:
    op.drop_index("ix_job_boosts_address", table_name="job_boosts")
    op.drop_index("ix_job_boosts_job_id", table_name="job_boosts")
    op.drop_table("job_boosts")

    op.drop_index("ix_agr_ledger_job_id", table_name="agr_ledger")
    op.drop_index("ix_agr_ledger_address", table_name="agr_ledger")
    op.drop_table("agr_ledger")

    op.drop_column("jobs", "featured_score")
    op.drop_column("jobs", "featured_until")

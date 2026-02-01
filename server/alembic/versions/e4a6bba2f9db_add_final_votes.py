"""add final votes

Revision ID: e4a6bba2f9db
Revises: 60df3ed26889
Create Date: 2026-01-17 16:42:04.918039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a6bba2f9db'
down_revision: Union[str, None] = '60df3ed26889'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "final_votes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("submission_id", sa.String(), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("voter_address", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("job_id", "voter_address", name="uq_final_votes_job_voter"),
    )
    op.create_index("ix_final_votes_job_id", "final_votes", ["job_id"])
    op.create_index("ix_final_votes_submission_id", "final_votes", ["submission_id"])
    op.create_index("ix_final_votes_voter_address", "final_votes", ["voter_address"])


def downgrade() -> None:
    op.drop_index("ix_final_votes_voter_address", table_name="final_votes")
    op.drop_index("ix_final_votes_submission_id", table_name="final_votes")
    op.drop_index("ix_final_votes_job_id", table_name="final_votes")
    op.drop_table("final_votes")

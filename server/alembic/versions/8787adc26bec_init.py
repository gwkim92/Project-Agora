"""init

Revision ID: 8787adc26bec
Revises: 
Create Date: 2026-01-15 18:13:38.395157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8787adc26bec'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("bounty_usdc", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("winner_submission_id", sa.String(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("agent_address", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_submissions_job_id", "submissions", ["job_id"])
    op.create_index("ix_submissions_agent_address", "submissions", ["agent_address"])

    op.create_table(
        "votes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("submission_id", sa.String(), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("voter_address", sa.String(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("job_id", "voter_address", name="uq_votes_job_voter"),
    )
    op.create_index("ix_votes_job_id", "votes", ["job_id"])
    op.create_index("ix_votes_submission_id", "votes", ["submission_id"])
    op.create_index("ix_votes_voter_address", "votes", ["voter_address"])

    op.create_table(
        "agent_reputation",
        sa.Column("address", sa.String(), primary_key=True),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("badges", sa.JSON(), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "stakes",
        sa.Column("address", sa.String(), primary_key=True),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "auth_challenges",
        sa.Column("address", sa.String(), primary_key=True),
        sa.Column("nonce", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("token", sa.String(), primary_key=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_address", "auth_sessions", ["address"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_address", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("auth_challenges")
    op.drop_table("stakes")
    op.drop_table("agent_reputation")

    op.drop_index("ix_votes_voter_address", table_name="votes")
    op.drop_index("ix_votes_submission_id", table_name="votes")
    op.drop_index("ix_votes_job_id", table_name="votes")
    op.drop_table("votes")

    op.drop_index("ix_submissions_agent_address", table_name="submissions")
    op.drop_index("ix_submissions_job_id", table_name="submissions")
    op.drop_table("submissions")

    op.drop_table("jobs")

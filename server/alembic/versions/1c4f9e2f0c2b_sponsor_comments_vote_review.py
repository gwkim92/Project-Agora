"""sponsor address, comments, and vote review

Revision ID: 1c4f9e2f0c2b
Revises: 4cadb52f32dc
Create Date: 2026-01-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c4f9e2f0c2b"
down_revision: Union[str, None] = "4cadb52f32dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # jobs.sponsor_address
    op.add_column("jobs", sa.Column("sponsor_address", sa.String(), nullable=True))
    op.create_index("ix_jobs_sponsor_address", "jobs", ["sponsor_address"])

    # votes.review (optional JSON)
    op.add_column("votes", sa.Column("review", sa.JSON(), nullable=True))

    # comments table (job/submission discussion)
    op.create_table(
        "comments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column("author_address", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.String(), nullable=True),
    )
    op.create_index("ix_comments_author_address", "comments", ["author_address"])
    op.create_index("ix_comments_target", "comments", ["target_type", "target_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_comments_target", table_name="comments")
    op.drop_index("ix_comments_author_address", table_name="comments")
    op.drop_table("comments")

    op.drop_column("votes", "review")

    op.drop_index("ix_jobs_sponsor_address", table_name="jobs")
    op.drop_column("jobs", "sponsor_address")


"""posts (community timeline)

Revision ID: c3f2a8b1d9aa
Revises: d7a3c6e1b204
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f2a8b1d9aa"
down_revision: Union[str, None] = "d7a3c6e1b204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_address", sa.String(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.String(), nullable=True),
    )
    op.create_index("ix_posts_author_address", "posts", ["author_address"])
    op.create_index("ix_posts_created_at", "posts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_posts_created_at", table_name="posts")
    op.drop_index("ix_posts_author_address", table_name="posts")
    op.drop_table("posts")


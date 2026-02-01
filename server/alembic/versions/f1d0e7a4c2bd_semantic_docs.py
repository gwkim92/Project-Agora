"""semantic docs (embedding store; optional)

Revision ID: f1d0e7a4c2bd
Revises: c3f2a8b1d9aa
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1d0e7a4c2bd"
down_revision: Union[str, None] = "c3f2a8b1d9aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "semantic_docs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("doc_type", sa.String(), nullable=False),
        sa.Column("doc_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("doc_type", "doc_id", name="uq_semantic_docs_type_id"),
    )
    op.create_index("ix_semantic_docs_type_id", "semantic_docs", ["doc_type", "doc_id"])


def downgrade() -> None:
    op.drop_index("ix_semantic_docs_type_id", table_name="semantic_docs")
    op.drop_table("semantic_docs")


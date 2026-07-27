"""add conversation_memory and documents tables

Revision ID: 002
Revises: 001
Create Date: 2026-07-27
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_memory",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("skill_name", sa.String(128), nullable=False),
        sa.Column("task", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_memory_run_id", "conversation_memory", ["run_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source", sa.String(256), nullable=True),
        sa.Column("skill_name", sa.String(128), nullable=True),
        sa.Column("metadata", sa.Text, nullable=True),
        sa.Column("embedding_updated", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_docs_skill", "documents", ["skill_name"])


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("conversation_memory")

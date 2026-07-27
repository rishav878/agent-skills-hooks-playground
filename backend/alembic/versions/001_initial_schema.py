"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-27
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("input", sa.Text, nullable=False),
        sa.Column("output", sa.Text, nullable=True),
        sa.Column("selected_skill", sa.String(128), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_runs_status", "agent_runs", ["status"])
    op.create_index("idx_runs_created_at", "agent_runs", ["created_at"])

    op.create_table(
        "execution_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("component", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("input", sa.Text, nullable=True),
        sa.Column("output", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("metadata", sa.Text, nullable=True),
    )
    op.create_index("idx_events_run_id", "execution_events", ["run_id"])
    op.create_index("idx_events_type", "execution_events", ["event_type"])
    op.create_index("idx_events_ts", "execution_events", ["timestamp"])

    op.create_table(
        "skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("instructions", sa.Text, nullable=False),
        sa.Column("input_schema", sa.Text, nullable=True),
        sa.Column("output_schema", sa.Text, nullable=True),
        sa.Column("allowed_tools", sa.Text, nullable=True),
        sa.Column("metadata", sa.Text, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "hooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("lifecycle_event", sa.String(32), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("metadata", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "tools",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("input_schema", sa.Text, nullable=True),
        sa.Column("output_schema", sa.Text, nullable=True),
        sa.Column("risk_level", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("permissions", sa.Text, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("skill_name", sa.String(128), nullable=False),
        sa.Column("input_summary", sa.Text, nullable=False),
        sa.Column("asker", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("state_snapshot", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("decided_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_approval_run", "approval_requests", ["run_id"])
    op.create_index("idx_approval_status", "approval_requests", ["status"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("label", sa.String(128), nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("approval_requests")
    op.drop_table("tools")
    op.drop_table("hooks")
    op.drop_table("skills")
    op.drop_table("execution_events")
    op.drop_table("agent_runs")

"""
add execution trace table

Revision ID: 0027_add_execution_trace_table
Revises: 0026_add_query_asset_constraint
Create Date: 2026-01-18 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027_add_execution_trace_table"
down_revision = "0026_add_query_asset_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_execution_trace",
        sa.Column("trace_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("parent_trace_id", sa.Text(), nullable=True),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("ops_mode", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'success'")
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(), nullable=True),
        sa.Column("applied_assets", postgresql.JSONB(), nullable=True),
        sa.Column("asset_versions", postgresql.JSONB(), nullable=True),
        sa.Column("fallbacks", postgresql.JSONB(), nullable=True),
        sa.Column("plan_raw", postgresql.JSONB(), nullable=True),
        sa.Column("plan_validated", postgresql.JSONB(), nullable=True),
        sa.Column("execution_steps", postgresql.JSONB(), nullable=True),
        sa.Column("references", postgresql.JSONB(), nullable=True),
        sa.Column("answer", postgresql.JSONB(), nullable=True),
        sa.Column("ui_render", postgresql.JSONB(), nullable=True),
        sa.Column("audit_links", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_execution_trace_created_at", "tb_execution_trace", ["created_at"]
    )
    op.create_index(
        "idx_execution_trace_parent", "tb_execution_trace", ["parent_trace_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_execution_trace_parent", table_name="tb_execution_trace")
    op.drop_index("idx_execution_trace_created_at", table_name="tb_execution_trace")
    op.drop_table("tb_execution_trace")

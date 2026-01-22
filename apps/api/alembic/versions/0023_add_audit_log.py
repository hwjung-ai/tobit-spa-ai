"""
add audit log table for request tracing and audit trail

Revision ID: 0023_add_audit_log
Revises: 0022_add_asset_registry
Create Date: 2026-01-16 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023_add_audit_log"
down_revision = "0022_add_asset_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tb_audit_log table
    op.create_table(
        "tb_audit_log",
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("parent_trace_id", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("changes", postgresql.JSONB(), nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("audit_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for common queries
    op.create_index("idx_audit_log_trace_id", "tb_audit_log", ["trace_id"])
    op.create_index(
        "idx_audit_log_resource",
        "tb_audit_log",
        ["resource_type", "resource_id"],
    )
    op.create_index("idx_audit_log_created_at", "tb_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_log_created_at", "tb_audit_log")
    op.drop_index("idx_audit_log_resource", "tb_audit_log")
    op.drop_index("idx_audit_log_trace_id", "tb_audit_log")
    op.drop_table("tb_audit_log")

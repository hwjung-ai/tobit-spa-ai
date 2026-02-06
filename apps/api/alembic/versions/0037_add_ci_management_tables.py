"""add CI management tables for change tracking, integrity validation, and duplicate detection"""

import sqlalchemy as sa
from alembic import op

revision = "0037_add_ci_management_tables"
down_revision = "0036_enhance_document_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create CI management tables."""
    # Create tb_ci_change table
    op.create_table(
        "tb_ci_change",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ci_id", sa.String(128), nullable=False),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("changed_by_user_id", sa.String(36), nullable=False),
        sa.Column("change_reason", sa.String(500), nullable=True),
        sa.Column("old_values", sa.Text(), nullable=True),
        sa.Column("new_values", sa.Text(), nullable=True),
        sa.Column("approved_by_user_id", sa.String(36), nullable=True),
        sa.Column("approval_notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
    )
    op.create_index("ix_tb_ci_change_ci_id", "tb_ci_change", ["ci_id"])
    op.create_index("ix_tb_ci_change_status", "tb_ci_change", ["status"])
    op.create_index("ix_tb_ci_change_created_at", "tb_ci_change", ["created_at"])
    op.create_index("ix_tb_ci_change_tenant_id", "tb_ci_change", ["tenant_id"])

    # Create tb_ci_integrity_issue table
    op.create_table(
        "tb_ci_integrity_issue",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ci_id", sa.String(128), nullable=False),
        sa.Column("issue_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(36), nullable=True),
        sa.Column("resolution_notes", sa.String(500), nullable=True),
        sa.Column("related_ci_ids", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
    )
    op.create_index(
        "ix_tb_ci_integrity_issue_ci_id", "tb_ci_integrity_issue", ["ci_id"]
    )
    op.create_index(
        "ix_tb_ci_integrity_issue_severity", "tb_ci_integrity_issue", ["severity"]
    )
    op.create_index(
        "ix_tb_ci_integrity_issue_is_resolved", "tb_ci_integrity_issue", ["is_resolved"]
    )
    op.create_index(
        "ix_tb_ci_integrity_issue_tenant_id", "tb_ci_integrity_issue", ["tenant_id"]
    )

    # Create tb_ci_duplicate table
    op.create_table(
        "tb_ci_duplicate",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ci_id_1", sa.String(128), nullable=False),
        sa.Column("ci_id_2", sa.String(128), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_merged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confirmed_by_user_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(20), nullable=True),
        sa.Column("merge_into_ci_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
    )
    op.create_index("ix_tb_ci_duplicate_ci_id_1", "tb_ci_duplicate", ["ci_id_1"])
    op.create_index("ix_tb_ci_duplicate_ci_id_2", "tb_ci_duplicate", ["ci_id_2"])
    op.create_index(
        "ix_tb_ci_duplicate_is_confirmed", "tb_ci_duplicate", ["is_confirmed"]
    )
    op.create_index("ix_tb_ci_duplicate_is_merged", "tb_ci_duplicate", ["is_merged"])
    op.create_index("ix_tb_ci_duplicate_tenant_id", "tb_ci_duplicate", ["tenant_id"])


def downgrade() -> None:
    """Drop CI management tables."""
    op.drop_table("tb_ci_duplicate")
    op.drop_table("tb_ci_integrity_issue")
    op.drop_table("tb_ci_change")

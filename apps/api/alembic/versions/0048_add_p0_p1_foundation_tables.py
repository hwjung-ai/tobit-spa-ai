"""add api versions, document search log, admin persistence tables

Revision ID: 0048_add_p0_p1_foundation_tables
Revises: 0047_add_document_search_indexes
Create Date: 2026-02-08 12:05:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0048_add_p0_p1_foundation_tables"
down_revision = "0047_add_document_search_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # API definition versions
    op.create_table(
        "api_definition_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("api_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.Text(), nullable=False, server_default="update"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_foreign_key(
        "fk_api_definition_versions_api_id",
        "api_definition_versions",
        "api_definitions",
        ["api_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_api_definition_versions_api_version",
        "api_definition_versions",
        ["api_id", "version"],
        unique=True,
    )
    op.create_index(
        "ix_api_definition_versions_created_at",
        "api_definition_versions",
        [sa.text("created_at DESC")],
    )

    # Document search logs (for analytics/suggestions)
    op.create_table(
        "document_search_log",
        sa.Column("search_id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("results_count", sa.Integer(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_document_search_log_tenant_query",
        "document_search_log",
        ["tenant_id", "query"],
    )
    op.create_index(
        "ix_document_search_log_created_at",
        "document_search_log",
        [sa.text("created_at DESC")],
    )

    # Document version metadata
    op.add_column("documents", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("documents", sa.Column("parent_id", sa.String(length=36), nullable=True))
    op.add_column("documents", sa.Column("version_comment", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_documents_parent_id",
        "documents",
        "documents",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_documents_parent_version", "documents", ["parent_id", "version"])

    # Admin settings persistence
    op.create_table(
        "tb_admin_setting",
        sa.Column("setting_key", sa.String(length=200), primary_key=True, nullable=False),
        sa.Column("setting_value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "tb_admin_setting_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("setting_key", sa.String(length=200), nullable=False),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=False),
        sa.Column("admin_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_tb_admin_setting_audit_key_created",
        "tb_admin_setting_audit",
        ["setting_key", sa.text("created_at DESC")],
    )

    # User activity logs
    op.create_table(
        "tb_user_activity_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("activity_data", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_foreign_key(
        "fk_tb_user_activity_log_user_id",
        "tb_user_activity_log",
        "tb_user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_tb_user_activity_log_user_created",
        "tb_user_activity_log",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_tb_user_activity_log_type_created",
        "tb_user_activity_log",
        ["activity_type", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_tb_user_activity_log_type_created", table_name="tb_user_activity_log")
    op.drop_index("ix_tb_user_activity_log_user_created", table_name="tb_user_activity_log")
    op.drop_constraint("fk_tb_user_activity_log_user_id", "tb_user_activity_log", type_="foreignkey")
    op.drop_table("tb_user_activity_log")

    op.drop_index("ix_tb_admin_setting_audit_key_created", table_name="tb_admin_setting_audit")
    op.drop_table("tb_admin_setting_audit")
    op.drop_table("tb_admin_setting")

    op.drop_index("ix_documents_parent_version", table_name="documents")
    op.drop_constraint("fk_documents_parent_id", "documents", type_="foreignkey")
    op.drop_column("documents", "version_comment")
    op.drop_column("documents", "parent_id")
    op.drop_column("documents", "version")

    op.drop_index("ix_document_search_log_created_at", table_name="document_search_log")
    op.drop_index("ix_document_search_log_tenant_query", table_name="document_search_log")
    op.drop_table("document_search_log")

    op.drop_index("ix_api_definition_versions_created_at", table_name="api_definition_versions")
    op.drop_index("ix_api_definition_versions_api_version", table_name="api_definition_versions")
    op.drop_constraint("fk_api_definition_versions_api_id", "api_definition_versions", type_="foreignkey")
    op.drop_table("api_definition_versions")

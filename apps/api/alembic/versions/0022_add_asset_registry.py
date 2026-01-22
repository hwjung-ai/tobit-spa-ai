"""
add asset registry tables

Revision ID: 0022_add_asset_registry
Revises: 0021_add_builder_to_thread
Create Date: 2026-01-16 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0022_add_asset_registry"
down_revision = "0021_add_builder_to_thread"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Create tb_asset_registry
    op.create_table(
        "tb_asset_registry",
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'draft'")),
        # Prompt fields
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("engine", sa.Text(), nullable=True),
        sa.Column("template", sa.Text(), nullable=True),
        sa.Column("input_schema", postgresql.JSONB(), nullable=True),
        sa.Column("output_contract", postgresql.JSONB(), nullable=True),
        # Mapping fields
        sa.Column("mapping_type", sa.Text(), nullable=True),
        sa.Column("content", postgresql.JSONB(), nullable=True),
        # Policy fields
        sa.Column("policy_type", sa.Text(), nullable=True),
        sa.Column("limits", postgresql.JSONB(), nullable=True),
        # Metadata
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("published_by", sa.Text(), nullable=True),
        sa.Column("published_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Constraints
        sa.CheckConstraint(
            "asset_type IN ('prompt', 'mapping', 'policy')",
            name="chk_asset_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published')",
            name="chk_status",
        ),
    )

    # Unique constraint for published assets
    op.create_index(
        "unique_published_name",
        "tb_asset_registry",
        ["asset_type", "name", "status"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )

    # Additional indexes
    op.create_index(
        "idx_asset_registry_type_status",
        "tb_asset_registry",
        ["asset_type", "status"],
    )
    op.create_index(
        "idx_asset_registry_name",
        "tb_asset_registry",
        ["name"],
    )
    op.create_index(
        "idx_asset_registry_published_at",
        "tb_asset_registry",
        [sa.text("published_at DESC")],
        postgresql_where=sa.text("status = 'published'"),
    )

    # Create tb_asset_version_history
    op.create_table(
        "tb_asset_version_history",
        sa.Column(
            "history_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("published_by", sa.Text(), nullable=True),
        sa.Column(
            "published_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("rollback_from_version", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["tb_asset_registry.asset_id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "idx_asset_history_asset_version",
        "tb_asset_version_history",
        ["asset_id", sa.text("version DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_asset_history_asset_version", table_name="tb_asset_version_history")
    op.drop_table("tb_asset_version_history")

    op.drop_index("idx_asset_registry_published_at", table_name="tb_asset_registry")
    op.drop_index("idx_asset_registry_name", table_name="tb_asset_registry")
    op.drop_index("idx_asset_registry_type_status", table_name="tb_asset_registry")
    op.drop_index("unique_published_name", table_name="tb_asset_registry")
    op.drop_table("tb_asset_registry")

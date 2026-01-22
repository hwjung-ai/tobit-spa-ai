"""
add operation settings table for runtime configuration management

Revision ID: 0024_add_operation_settings
Revises: 0023_add_audit_log
Create Date: 2026-01-16 13:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0024_add_operation_settings"
down_revision = "0023_add_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tb_operation_settings table
    op.create_table(
        "tb_operation_settings",
        sa.Column(
            "setting_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("setting_key", sa.Text(), nullable=False, unique=True),
        sa.Column("setting_value", postgresql.JSONB(), nullable=False),
        sa.Column(
            "source",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'published'"),
        ),
        sa.Column(
            "env_override",
            postgresql.JSONB(),
            nullable=True,
        ),
        sa.Column("restart_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "published_by",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes
    op.create_index("idx_operation_settings_key", "tb_operation_settings", ["setting_key"])
    op.create_index("idx_operation_settings_source", "tb_operation_settings", ["source"])


def downgrade() -> None:
    op.drop_index("idx_operation_settings_source", "tb_operation_settings")
    op.drop_index("idx_operation_settings_key", "tb_operation_settings")
    op.drop_table("tb_operation_settings")

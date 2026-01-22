"""add permission management tables"""

import sqlalchemy as sa
from alembic import op

revision = "0033_add_permission_tables"
down_revision = "0032_add_api_keys_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create permission management tables."""
    # Create tb_role_permission table
    op.create_table(
        "tb_role_permission",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("permission", sa.String(50), nullable=False),
        sa.Column("is_granted", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices for tb_role_permission
    op.create_index("ix_tb_role_permission_role", "tb_role_permission", ["role"])
    op.create_index("ix_tb_role_permission_permission", "tb_role_permission", ["permission"])
    op.create_index(
        "ix_tb_role_permission_role_permission",
        "tb_role_permission",
        ["role", "permission"],
    )

    # Create tb_resource_permission table
    op.create_table(
        "tb_resource_permission",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("permission", sa.String(50), nullable=False),
        sa.Column("is_granted", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tb_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices for tb_resource_permission
    op.create_index("ix_tb_resource_permission_user_id", "tb_resource_permission", ["user_id"])
    op.create_index(
        "ix_tb_resource_permission_user_resource",
        "tb_resource_permission",
        ["user_id", "resource_type", "resource_id"],
    )
    op.create_index("ix_tb_resource_permission_permission", "tb_resource_permission", ["permission"])
    op.create_index("ix_tb_resource_permission_expires", "tb_resource_permission", ["expires_at"])


def downgrade() -> None:
    """Drop permission management tables."""
    op.drop_index("ix_tb_resource_permission_expires", "tb_resource_permission")
    op.drop_index("ix_tb_resource_permission_permission", "tb_resource_permission")
    op.drop_index("ix_tb_resource_permission_user_resource", "tb_resource_permission")
    op.drop_index("ix_tb_resource_permission_user_id", "tb_resource_permission")
    op.drop_table("tb_resource_permission")

    op.drop_index("ix_tb_role_permission_role_permission", "tb_role_permission")
    op.drop_index("ix_tb_role_permission_permission", "tb_role_permission")
    op.drop_index("ix_tb_role_permission_role", "tb_role_permission")
    op.drop_table("tb_role_permission")

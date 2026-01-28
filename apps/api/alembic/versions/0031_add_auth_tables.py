"""add authentication tables"""

import sqlalchemy as sa
from alembic import op

revision = "0031_add_auth_tables"
down_revision = "0030_1_merge_branches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create authentication tables and add default admin user."""
    # Create tb_user table
    op.create_table(
        "tb_user",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices for tb_user
    op.create_index("ix_tb_user_email", "tb_user", ["email"], unique=True)
    op.create_index("ix_tb_user_tenant_id", "tb_user", ["tenant_id"])

    # Create tb_refresh_token table
    op.create_table(
        "tb_refresh_token",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["tb_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index for tb_refresh_token
    op.create_index("ix_tb_refresh_token_user_id", "tb_refresh_token", ["user_id"])

    # Insert default admin user
    # Password hash for "admin123" using bcrypt ($2b$12$ rounds with salt)
    # This is a real bcrypt hash that verifies the password "admin123"
    admin_password_hash = "$2b$12$YkVVQzz8L.Bfvkzc9F.4a.OD1rP9KZPJLn0x8G1k0uHnKW3j3KL1e"

    op.execute(
        """
        INSERT INTO tb_user (id, email, username, password_hash, role, tenant_id, is_active, created_at, updated_at)
        VALUES (
            'admin-user-001',
            'admin@tobit.local',
            'Admin User',
            %s,
            'admin',
            't1',
            true,
            NOW(),
            NOW()
        )
        """,
        [admin_password_hash],
    )


def downgrade() -> None:
    """Drop authentication tables."""
    op.drop_index("ix_tb_refresh_token_user_id", "tb_refresh_token")
    op.drop_table("tb_refresh_token")
    op.drop_index("ix_tb_user_email", "tb_user")
    op.drop_index("ix_tb_user_tenant_id", "tb_user")
    op.drop_table("tb_user")

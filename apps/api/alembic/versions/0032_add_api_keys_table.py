"""add api_keys table for programmatic access"""

from alembic import op
import sqlalchemy as sa

revision = "0032_add_api_keys_table"
down_revision = "0031_add_auth_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create API Keys table."""
    op.create_table(
        "tb_api_key",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("scope", sa.String(1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_trace_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tb_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices for efficient lookups
    op.create_index("ix_tb_api_key_user_id", "tb_api_key", ["user_id"])
    op.create_index("ix_tb_api_key_key_prefix", "tb_api_key", ["key_prefix"])
    op.create_index("ix_tb_api_key_is_active", "tb_api_key", ["is_active"])


def downgrade() -> None:
    """Drop API Keys table."""
    op.drop_index("ix_tb_api_key_is_active", "tb_api_key")
    op.drop_index("ix_tb_api_key_key_prefix", "tb_api_key")
    op.drop_index("ix_tb_api_key_user_id", "tb_api_key")
    op.drop_table("tb_api_key")

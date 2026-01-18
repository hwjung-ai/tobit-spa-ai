"""add encryption fields to tb_user for encrypted email and phone"""

from alembic import op
import sqlalchemy as sa

revision = "0034_add_encryption_fields"
down_revision = "0033_add_permission_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add encrypted email and phone fields to tb_user."""
    # Add new encrypted columns
    op.add_column(
        "tb_user",
        sa.Column("email_encrypted", sa.String(512), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_user",
        sa.Column("phone_encrypted", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    """Remove encrypted email and phone fields from tb_user."""
    op.drop_column("tb_user", "phone_encrypted")
    op.drop_column("tb_user", "email_encrypted")

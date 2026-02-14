"""Add tenant_id to tb_asset_registry for multi-tenant isolation.

Revision ID: 0050
"""

from alembic import op
import sqlalchemy as sa


revision = "0050"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tb_asset_registry",
        sa.Column("tenant_id", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_tb_asset_registry_tenant_id",
        "tb_asset_registry",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tb_asset_registry_tenant_id", table_name="tb_asset_registry")
    op.drop_column("tb_asset_registry", "tenant_id")

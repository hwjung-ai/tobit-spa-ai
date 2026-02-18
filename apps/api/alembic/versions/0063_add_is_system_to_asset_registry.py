"""Add is_system to asset registry

Revision ID: 0063
Revises: 0062_repair_missing_tool_catalog_ref
Create Date: 2026-02-18

System assets (plan_budget, view_depth) cannot be deleted or renamed.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0063"
down_revision = "0062_repair_missing_tool_catalog_ref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_system column
    op.add_column(
        "tb_asset_registry",
        sa.Column("is_system", sa.Integer, nullable=False, server_default=sa.text("0")),
    )

    # Mark existing system policies as system assets
    op.execute(
        """
        UPDATE tb_asset_registry
        SET is_system = 1
        WHERE asset_type = 'policy'
        AND policy_type IN ('plan_budget', 'view_depth')
        """
    )


def downgrade() -> None:
    op.drop_column("tb_asset_registry", "is_system")

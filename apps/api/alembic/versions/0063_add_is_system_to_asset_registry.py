"""Add is_system to asset registry

Revision ID: 0063
Revises: 0062_repair_missing_tool_catalog_ref
Create Date: 2026-02-18

System assets cannot be deleted or renamed:
- Policies: plan_budget, view_depth, discovery_config
- Mappings: graph_relation, graph_relation_allowlist
"""
import sqlalchemy as sa
from alembic import op

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

    # Mark system policies as protected
    op.execute(
        """
        UPDATE tb_asset_registry
        SET is_system = 1
        WHERE asset_type = 'policy'
        AND policy_type IN ('plan_budget', 'view_depth', 'discovery_config')
        """
    )

    # Mark system mappings as protected
    op.execute(
        """
        UPDATE tb_asset_registry
        SET is_system = 1
        WHERE asset_type = 'mapping'
        AND name IN ('graph_relation', 'graph_relation_allowlist')
        """
    )


def downgrade() -> None:
    op.drop_column("tb_asset_registry", "is_system")

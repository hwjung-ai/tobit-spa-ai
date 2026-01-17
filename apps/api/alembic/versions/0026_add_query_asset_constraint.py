"""
add query to asset_type constraint

Revision ID: 0026_add_query_asset_constraint
Revises: 0025_add_query_asset_fields
Create Date: 2026-01-17 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0026_add_query_asset_constraint"
down_revision = "0025_add_query_asset_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old constraint
    op.drop_constraint("chk_asset_type", "tb_asset_registry", type_="check")

    # Add the new constraint with 'query' included
    op.create_check_constraint(
        "chk_asset_type",
        "tb_asset_registry",
        "asset_type IN ('prompt', 'mapping', 'policy', 'query')",
    )


def downgrade() -> None:
    # Drop the new constraint
    op.drop_constraint("chk_asset_type", "tb_asset_registry", type_="check")

    # Restore the old constraint
    op.create_check_constraint(
        "chk_asset_type",
        "tb_asset_registry",
        "asset_type IN ('prompt', 'mapping', 'policy')",
    )

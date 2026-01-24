"""Add source asset type

Revision ID: 0039
Revises: 0038
Create Date: 2026-01-22 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "0039_add_source_asset_type"
down_revision = "0038_add_orchestration_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source asset type as a valid value in the tb_asset_registry table
    # The asset_type column already exists, we're just documenting that 'source' is now supported
    pass


def downgrade() -> None:
    pass

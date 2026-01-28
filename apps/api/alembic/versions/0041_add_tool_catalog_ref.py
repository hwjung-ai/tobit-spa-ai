"""Add tool_catalog_ref field to tb_asset_registry

Revision ID: 0041_add_tool_catalog_ref
Revises: 0040_add_multi_source_query_fields
Create Date: 2026-01-28 23:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0041_add_tool_catalog_ref'
down_revision = '0040_add_multi_source_query_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tool_catalog_ref column to tb_asset_registry
    op.add_column('tb_asset_registry', sa.Column('tool_catalog_ref', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove tool_catalog_ref column from tb_asset_registry
    op.drop_column('tb_asset_registry', 'tool_catalog_ref')

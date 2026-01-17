"""
add screen asset fields to asset registry
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0029_add_screen_asset_fields'
down_revision = '0028_add_flow_spans_column'
branch_labels = None
depends_on = None


def upgrade():
    # Add screen_id, schema_json, and tags columns to tb_asset_registry
    op.add_column('tb_asset_registry', sa.Column('screen_id', sa.Text(), nullable=True))
    op.add_column('tb_asset_registry', sa.Column('schema_json', sa.JSON(), nullable=True))
    op.add_column('tb_asset_registry', sa.Column('tags', sa.JSON(), nullable=True))

    # Create index on screen_id for fast lookups
    op.create_index('ix_asset_registry_screen_id', 'tb_asset_registry', ['screen_id'])


def downgrade():
    op.drop_index('ix_asset_registry_screen_id', table_name='tb_asset_registry')
    op.drop_column('tb_asset_registry', 'tags')
    op.drop_column('tb_asset_registry', 'schema_json')
    op.drop_column('tb_asset_registry', 'screen_id')

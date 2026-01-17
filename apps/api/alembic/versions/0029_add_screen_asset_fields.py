"""
add screen asset fields to asset registry
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0029_add_screen_asset_fields'
down_revision = '0022_add_asset_registry'
branch_labels = None
depends_on = None


def upgrade():
    # Add screen_id and schema_json columns to tb_asset_registry
    op.add_column('tb_asset_registry', sa.Column('screen_id', sa.Text(), nullable=True))
    op.add_column('tb_asset_registry', sa.Column('schema_json', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('tb_asset_registry', 'schema_json')
    op.drop_column('tb_asset_registry', 'screen_id')

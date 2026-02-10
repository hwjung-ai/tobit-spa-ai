"""add_api_linkage_to_asset_registry

Revision ID: 0051
Revises: 0050
Create Date: 2026-02-10 15:41:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = '0051'
down_revision: Union[str, None] = '0050'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = '0050'


def upgrade() -> None:
    """Add API Manager linkage fields to tb_asset_registry table."""
    op.add_column('tb_asset_registry',
        sa.Column('linked_from_api_id', sqlmodel.sql.sqltypes.UUID(), nullable=True))
    op.add_column('tb_asset_registry',
        sa.Column('linked_from_api_name', sa.Text(), nullable=True))
    op.add_column('tb_asset_registry',
        sa.Column('linked_from_api_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('tb_asset_registry',
        sa.Column('import_mode', sa.Text(), nullable=True))
    op.add_column('tb_asset_registry',
        sa.Column('last_synced_at', sa.TIMESTAMP(timezone=True), nullable=True))
    
    # Add foreign key constraint to api_definitions
    op.create_foreign_key(
        'fk_asset_linked_from_api',
        'tb_asset_registry', 'api_definitions',
        ['linked_from_api_id'], ['id']
    )


def downgrade() -> None:
    """Remove API Manager linkage fields from tb_asset_registry table."""
    op.drop_constraint('fk_asset_linked_from_api', 'tb_asset_registry', type_='foreignkey')
    op.drop_column('tb_asset_registry', 'last_synced_at')
    op.drop_column('tb_asset_registry', 'import_mode')
    op.drop_column('tb_asset_registry', 'linked_from_api_at')
    op.drop_column('tb_asset_registry', 'linked_from_api_name')
    op.drop_column('tb_asset_registry', 'linked_from_api_id')
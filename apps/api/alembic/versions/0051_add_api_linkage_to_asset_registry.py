"""add_api_linkage_to_asset_registry

Revision ID: 0051
Revises: 0050
Create Date: 2026-02-10 15:41:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0051'
down_revision: Union[str, None] = '0050'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add API Manager linkage fields to tb_asset_registry table."""
    op.add_column('tb_asset_registry',
        sa.Column('linked_from_api_id', sa.UUID(), nullable=True))
    op.add_column('tb_asset_registry',
        sa.Column('linked_from_api_name', sa.Text(), nullable=True))
    op.add_column('tb_asset_registry',
        sa.Column('linked_from_api_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('tb_asset_registry',
        sa.Column('import_mode', sa.Text(), nullable=True))
    op.add_column('tb_asset_registry',
        sa.Column('last_synced_at', sa.TIMESTAMP(timezone=True), nullable=True))
    
    # No FK constraint - managed at application level to avoid bidirectional FK issues
    # when unlinking. Linkage is enforced by business logic.


def downgrade() -> None:
    """Remove API Manager linkage fields from tb_asset_registry table."""
    op.drop_column('tb_asset_registry', 'last_synced_at')
    op.drop_column('tb_asset_registry', 'import_mode')
    op.drop_column('tb_asset_registry', 'linked_from_api_at')
    op.drop_column('tb_asset_registry', 'linked_from_api_name')
    op.drop_column('tb_asset_registry', 'linked_from_api_id')

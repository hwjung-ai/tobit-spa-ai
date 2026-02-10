"""add_tools_linkage_to_api_definitions

Revision ID: 0050
Revises: 0049
Create Date: 2026-02-10 15:22:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = '0050'
down_revision: Union[str, None] = '0049'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = '0049'


def upgrade() -> None:
    """Add tools linkage fields to api_definitions table."""
    op.add_column('api_definitions', 
        sa.Column('linked_to_tool_id', sqlmodel.sql.sqltypes.UUID(), nullable=True))
    op.add_column('api_definitions',
        sa.Column('linked_to_tool_name', sa.Text(), nullable=True))
    op.add_column('api_definitions',
        sa.Column('linked_at', sa.DateTime(), nullable=True))
    
    # Add foreign key constraint to asset_registry
    op.create_foreign_key(
        'fk_api_def_linked_tool',
        'api_definitions', 'tb_asset_registry',
        ['linked_to_tool_id'], ['asset_id']
    )


def downgrade() -> None:
    """Remove tools linkage fields from api_definitions table."""
    op.drop_constraint('fk_api_def_linked_tool', 'api_definitions', type_='foreignkey')
    op.drop_column('api_definitions', 'linked_at')
    op.drop_column('api_definitions', 'linked_to_tool_name')
    op.drop_column('api_definitions', 'linked_to_tool_id')
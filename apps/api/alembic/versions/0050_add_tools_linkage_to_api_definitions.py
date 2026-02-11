"""add_tools_linkage_to_api_definitions

Revision ID: 0050
Revises: 0049
Create Date: 2026-02-10 15:22:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0050'
down_revision: Union[str, None] = '0049_add_api_definitions_runtime_policy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tools linkage fields to api_definitions table."""
    op.add_column('api_definitions', 
        sa.Column('linked_to_tool_id', sa.UUID(), nullable=True))
    op.add_column('api_definitions',
        sa.Column('linked_to_tool_name', sa.Text(), nullable=True))
    op.add_column('api_definitions',
        sa.Column('linked_at', sa.DateTime(), nullable=True))
    
    # No FK constraint - managed at application level to avoid bidirectional FK issues
    # when unlinking. Linkage is enforced by business logic.


def downgrade() -> None:
    """Remove tools linkage fields from api_definitions table."""
    op.drop_column('api_definitions', 'linked_at')
    op.drop_column('api_definitions', 'linked_to_tool_name')
    op.drop_column('api_definitions', 'linked_to_tool_id')

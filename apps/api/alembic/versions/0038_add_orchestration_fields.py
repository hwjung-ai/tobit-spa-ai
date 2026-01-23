"""Add orchestration fields to tb_execution_trace

Revision ID: 0038
Revises: 0037
Create Date: 2026-01-22 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0038_add_orchestration_fields'
down_revision = '0037_add_document_access_and_search_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to tb_execution_trace table
    op.add_column('tb_execution_trace', sa.Column('route', sa.Text(), nullable=True))
    op.add_column('tb_execution_trace', sa.Column('stage_inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text('[]')))
    op.add_column('tb_execution_trace', sa.Column('stage_outputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text('[]')))
    op.add_column('tb_execution_trace', sa.Column('replan_events', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text('[]')))
    op.add_column('tb_execution_trace', sa.Column('flow_spans', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('tb_execution_trace', 'flow_spans')
    op.drop_column('tb_execution_trace', 'replan_events')
    op.drop_column('tb_execution_trace', 'stage_outputs')
    op.drop_column('tb_execution_trace', 'stage_inputs')
    op.drop_column('tb_execution_trace', 'route')

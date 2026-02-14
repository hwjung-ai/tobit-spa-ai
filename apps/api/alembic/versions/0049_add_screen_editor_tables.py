"""Add Screen Editor tables

Revision ID: 0049
Revises: 0048_add_timeseries_metric_table
Create Date: 2026-02-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0049_add_screen_editor'
down_revision: Union[str, None] = '0048_add_timeseries_metric_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tb_screen table
    op.create_table(
        'tb_screen',
        sa.Column('screen_id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('screen_name', sa.String(255), nullable=False),
        sa.Column('screen_type', sa.String(50), nullable=False, server_default='custom'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('schema_version', sa.String(20), nullable=False, server_default='1.0'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('published_by', sa.String(255), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('components', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('layout', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('state', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('bindings', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('actions', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('styles', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('meta', postgresql.JSONB(), nullable=False, server_default='{}'),
    )

    # Create indexes for tb_screen
    op.create_index('ix_tb_screen_tenant_id', 'tb_screen', ['tenant_id'])
    op.create_index('ix_tb_screen_screen_name', 'tb_screen', ['screen_name'])
    op.create_index('ix_tb_screen_screen_type', 'tb_screen', ['screen_type'])
    op.create_index('ix_tb_screen_is_active', 'tb_screen', ['is_active'])
    op.create_index('ix_tb_screen_is_published', 'tb_screen', ['is_published'])
    op.create_index('ix_tb_screen_updated_at', 'tb_screen', ['updated_at'])

    # Create tb_screen_version table
    op.create_table(
        'tb_screen_version',
        sa.Column('version_id', sa.String(36), primary_key=True),
        sa.Column('screen_id', sa.String(36), sa.ForeignKey('tb_screen.screen_id'), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('snapshot', postgresql.JSONB(), nullable=False, server_default='{}'),
    )

    # Create indexes for tb_screen_version
    op.create_index('ix_tb_screen_version_screen_id', 'tb_screen_version', ['screen_id'])
    op.create_index('ix_tb_screen_version_tenant_id', 'tb_screen_version', ['tenant_id'])
    op.create_index('uq_tb_screen_version', 'tb_screen_version', ['screen_id', 'version'], unique=True)

    # Create tb_screen_audit_log table
    op.create_table(
        'tb_screen_audit_log',
        sa.Column('log_id', sa.String(36), primary_key=True),
        sa.Column('screen_id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('version_from', sa.Integer(), nullable=True),
        sa.Column('version_to', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
    )

    # Create indexes for tb_screen_audit_log
    op.create_index('ix_tb_screen_audit_log_screen_id', 'tb_screen_audit_log', ['screen_id'])
    op.create_index('ix_tb_screen_audit_log_tenant_id', 'tb_screen_audit_log', ['tenant_id'])
    op.create_index('ix_tb_screen_audit_log_timestamp', 'tb_screen_audit_log', ['timestamp'])
    op.create_index('ix_tb_screen_audit_log_action', 'tb_screen_audit_log', ['action'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_tb_screen_audit_log_action', 'tb_screen_audit_log')
    op.drop_index('ix_tb_screen_audit_log_timestamp', 'tb_screen_audit_log')
    op.drop_index('ix_tb_screen_audit_log_tenant_id', 'tb_screen_audit_log')
    op.drop_index('ix_tb_screen_audit_log_screen_id', 'tb_screen_audit_log')
    op.drop_table('tb_screen_audit_log')

    op.drop_index('uq_tb_screen_version', 'tb_screen_version')
    op.drop_index('ix_tb_screen_version_tenant_id', 'tb_screen_version')
    op.drop_index('ix_tb_screen_version_screen_id', 'tb_screen_version')
    op.drop_table('tb_screen_version')

    op.drop_index('ix_tb_screen_updated_at', 'tb_screen')
    op.drop_index('ix_tb_screen_is_published', 'tb_screen')
    op.drop_index('ix_tb_screen_is_active', 'tb_screen')
    op.drop_index('ix_tb_screen_screen_type', 'tb_screen')
    op.drop_index('ix_tb_screen_screen_name', 'tb_screen')
    op.drop_index('ix_tb_screen_tenant_id', 'tb_screen')
    op.drop_table('tb_screen')

"""Add ML Models Registry Table

Revision ID: 0049_add_ml_models_table
Revises: 0048_add_timeseries_metric_table
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa
from sqlmodel import SQLModel


# revision identifiers, used by Alembic.
revision = '0049_add_ml_models_table'
down_revision = '0048_add_timeseries_metric_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ML models registry table."""

    # Create tb_ml_models table
    op.create_table(
        'tb_ml_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_key', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('service', sa.String(), nullable=False),
        sa.Column('model_type', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('model_blob', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('feature_names', sa.Text(), nullable=True),
        sa.Column('target_names', sa.Text(), nullable=True),
        sa.Column('r2_score', sa.Float(), nullable=False),
        sa.Column('mape', sa.Float(), nullable=False),
        sa.Column('rmse', sa.Float(), nullable=False),
        sa.Column('mae', sa.Float(), nullable=False),
        sa.Column('coverage_90', sa.Float(), nullable=False),
        sa.Column('training_samples', sa.Integer(), nullable=False),
        sa.Column('training_config', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True, server_default='{}'),
        sa.Column('notes', sa.Text(), nullable=True, server_default=''),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes
    op.create_index('ix_tb_ml_models_model_key', 'tb_ml_models', ['model_key'])
    op.create_index('ix_tb_ml_models_tenant_id', 'tb_ml_models', ['tenant_id'])
    op.create_index('ix_tb_ml_models_service', 'tb_ml_models', ['service'])
    op.create_index('ix_tb_ml_models_model_type', 'tb_ml_models', ['model_type'])
    op.create_index('ix_tb_ml_models_version', 'tb_ml_models', ['version'])
    op.create_index('ix_tb_ml_models_is_active', 'tb_ml_models', ['is_active'])


def downgrade() -> None:
    """Drop ML models registry table."""

    op.drop_index('ix_tb_ml_models_is_active', table_name='tb_ml_models')
    op.drop_index('ix_tb_ml_models_version', table_name='tb_ml_models')
    op.drop_index('ix_tb_ml_models_model_type', table_name='tb_ml_models')
    op.drop_index('ix_tb_ml_models_service', table_name='tb_ml_models')
    op.drop_index('ix_tb_ml_models_tenant_id', table_name='tb_ml_models')
    op.drop_index('ix_tb_ml_models_model_key', table_name='tb_ml_models')

    op.drop_table('tb_ml_models')

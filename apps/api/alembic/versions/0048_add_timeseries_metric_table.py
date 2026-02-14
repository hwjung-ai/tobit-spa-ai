"""Add timeseries metric table for simulation

Revision ID: 0048_add_timeseries_metric_table
Revises: 0047_add_document_search_indexes
Create Date: 2026-02-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0048_add_timeseries_metric_table'
down_revision = '0047_add_document_search_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create timeseries metric table with indexes."""
    op.create_table(
        'tb_metric_timeseries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Text(), nullable=False, index=True, comment='Tenant identifier'),
        sa.Column('service', sa.Text(), nullable=False, index=True, comment='Service name (e.g., api-gateway)'),
        sa.Column('metric_name', sa.Text(), nullable=False, index=True, comment='Metric name (latency_ms, throughput_rps, error_rate_pct, cost_usd_hour)'),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False, index=True, comment='Measurement timestamp'),
        sa.Column('value', sa.Float(), nullable=False, comment='Metric value'),
        sa.Column('unit', sa.Text(), nullable=True, comment='Unit (ms, rps, %, USD/h)'),
        sa.Column('tags', postgresql.JSONB(), nullable=True, comment='Additional metadata tags'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        comment='Timeseries metric data for simulation baseline and backtesting'
    )

    # Create composite index for time-series queries
    op.create_index(
        'idx_tb_metric_timeseries_service_metric_time',
        'tb_metric_timeseries',
        ['service', 'metric_name', 'timestamp']
    )

    # Create index for baseline window queries
    op.create_index(
        'idx_tb_metric_timeseries_tenant_time',
        'tb_metric_timeseries',
        ['tenant_id', 'timestamp']
    )

    # Seed initial baseline data for sample services
    op.execute("""
        INSERT INTO tb_metric_timeseries (id, tenant_id, service, metric_name, timestamp, value, unit, tags)
        SELECT
            gen_random_uuid() as id,
            'default' as tenant_id,
            service,
            metric_name,
            NOW() - (INTERVAL '1 hour' * ROW_NUMBER() OVER (PARTITION BY service ORDER BY metric_name)) as timestamp,
            value,
            unit,
            '{"baseline": true}'::jsonb as tags
        FROM (VALUES
            ('api-gateway', 'latency_ms', 45.0, 'ms'),
            ('api-gateway', 'throughput_rps', 120.0, 'rps'),
            ('api-gateway', 'error_rate_pct', 0.5, '%'),
            ('api-gateway', 'cost_usd_hour', 12.5, 'USD/h'),
            ('order-service', 'latency_ms', 35.0, 'ms'),
            ('order-service', 'throughput_rps', 95.0, 'rps'),
            ('order-service', 'error_rate_pct', 0.3, '%'),
            ('order-service', 'cost_usd_hour', 8.2, 'USD/h'),
            ('payment-service', 'latency_ms', 28.0, 'ms'),
            ('payment-service', 'throughput_rps', 75.0, 'rps'),
            ('payment-service', 'error_rate_pct', 0.2, '%'),
            ('payment-service', 'cost_usd_hour', 6.5, 'USD/h')
        ) AS seed_data(service, metric_name, value, unit)
    """)


def downgrade() -> None:
    """Drop timeseries metric table."""
    op.drop_index('idx_tb_metric_timeseries_service_metric_time', table_name='tb_metric_timeseries')
    op.drop_index('idx_tb_metric_timeseries_tenant_time', table_name='tb_metric_timeseries')
    op.drop_table('tb_metric_timeseries')

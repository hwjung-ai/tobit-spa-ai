"""create tb_api_def table

Revision ID: 0010_create_tb_api_def
Revises: 0009_add_ops_history
Create Date: 2025-12-31 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0010_create_tb_api_def"
down_revision = "0009_add_ops_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_api_def",
        sa.Column(
            "api_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("api_name", sa.Text(), nullable=False),
        sa.Column("api_type", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("logic_type", sa.Text(), nullable=False),
        sa.Column("logic_body", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint("uq_tb_api_endpoint", "tb_api_def", ["endpoint"])
    op.execute(
        """
        INSERT INTO tb_api_def (api_id, api_name, api_type, method, endpoint, logic_type, logic_body, description, tags, is_active, created_by)
        VALUES
        (
            '00000000-0000-0000-0000-000000000001',
            'Metrics digest',
            'system',
            'GET',
            '/api-manager/metrics-summary',
            'sql',
            $$SELECT metric_name, MAX(value) AS peak, MIN(value) AS trough
              FROM metric_value
              WHERE time >= now() - interval '1 day'
              GROUP BY metric_name$$,
            'Daily metrics digest',
            '["ops","metrics"]'::jsonb,
            true,
            'ops-builder'
        ),
        (
            '00000000-0000-0000-0000-000000000002',
            'Configuration inventory',
            'custom',
            'GET',
            '/api-manager/config-inventory',
            'sql',
            $$SELECT tenant_id, COUNT(*) AS ci_count
              FROM ci
              WHERE deleted_at IS NULL
              GROUP BY tenant_id$$,
            'Tenant-level CI counts for ops',
            '["ops","config","mvp"]'::jsonb,
            true,
            'ops-builder'
        );
        """
    )


def downgrade() -> None:
    op.drop_table("tb_api_def")

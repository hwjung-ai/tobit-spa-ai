"""create ops metric tables

Revision ID: 0007_add_ops_metrics
Revises: 0006_add_ops_ci
Create Date: 2025-12-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0007_add_ops_metrics"
down_revision = "0006_add_ops_ci"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.create_table(
        "metric_def",
        sa.Column(
            "metric_id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("metric_name", sa.Text(), nullable=False, unique=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "value_type",
            sa.Enum("gauge", "counter", name="metric_value_type"),
            nullable=False,
            server_default="gauge",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "metric_value",
        sa.Column(
            "time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'t1'"),
        ),
        sa.Column(
            "ci_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("ci.ci_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "metric_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("metric_def.metric_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("quality", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=True,
        ),
    )

    op.execute(
        "SELECT create_hypertable('metric_value', 'time', if_not_exists => TRUE, chunk_time_interval => interval '1 day')"
    )


def downgrade() -> None:
    op.drop_table("metric_value")
    op.drop_table("metric_def")
    op.execute("DROP TYPE IF EXISTS metric_value_type")

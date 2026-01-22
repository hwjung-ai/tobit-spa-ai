"""create ops event table

Revision ID: 0008_add_ops_events
Revises: 0007_add_ops_metrics
Create Date: 2025-12-30 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0008_add_ops_events"
down_revision = "0007_add_ops_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_log",
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
            sa.ForeignKey("ci.ci_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("device", "cep", "system", name="event_source"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), nullable=True),
    )

    op.execute(
        "SELECT create_hypertable('event_log', 'time', if_not_exists => TRUE, chunk_time_interval => interval '12 hours')"
    )


def downgrade() -> None:
    op.drop_table("event_log")
    op.execute("DROP TYPE IF EXISTS event_source")

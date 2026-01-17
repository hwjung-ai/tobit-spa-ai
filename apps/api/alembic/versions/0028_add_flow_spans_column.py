"""
add flow_spans column for execution flow visualization

Revision ID: 0028_add_flow_spans_column
Revises: 0027_add_execution_trace_table
Create Date: 2026-01-18 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0028_add_flow_spans_column"
down_revision = "0027_add_execution_trace_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tb_execution_trace",
        sa.Column("flow_spans", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tb_execution_trace", "flow_spans")

"""Add trace_id column to query_history table.

Revision ID: 0042_add_trace_id_to_query_history
Revises: 0041_add_tool_catalog_ref
Create Date: 2026-01-29 18:25:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0042_add_trace_id_to_query_history"
down_revision = "0041_add_tool_catalog_ref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add trace_id column to query_history table
    op.add_column(
        "query_history",
        sa.Column("trace_id", sa.Text, nullable=True),
    )


def downgrade() -> None:
    # Remove trace_id column from query_history table
    op.drop_column("query_history", "trace_id")

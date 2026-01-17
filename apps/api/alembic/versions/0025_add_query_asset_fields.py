"""
add query asset fields to tb_asset_registry table

Revision ID: 0025_add_query_asset_fields
Revises: 0024_add_operation_settings
Create Date: 2026-01-17 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0025_add_query_asset_fields"
down_revision = "0024_add_operation_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add query asset fields to tb_asset_registry
    op.add_column(
        "tb_asset_registry",
        sa.Column("query_sql", sa.Text(), nullable=True),
    )
    op.add_column(
        "tb_asset_registry",
        sa.Column(
            "query_params",
            postgresql.JSONB(),
            nullable=True,
        ),
    )
    op.add_column(
        "tb_asset_registry",
        sa.Column(
            "query_metadata",
            postgresql.JSONB(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tb_asset_registry", "query_metadata")
    op.drop_column("tb_asset_registry", "query_params")
    op.drop_column("tb_asset_registry", "query_sql")

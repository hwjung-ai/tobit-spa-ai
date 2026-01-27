"""
Add multi-source query fields to tb_asset_registry table

Revision ID: 0040_add_multi_source_query_fields
Revises: 0039_add_source_asset_type
Create Date: 2026-01-26 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0040_add_multi_source_query_fields"
down_revision = "0039_add_source_asset_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add query_cypher for Neo4j queries
    op.add_column(
        "tb_asset_registry",
        sa.Column("query_cypher", sa.Text(), nullable=True),
    )
    # Add query_http for REST/GraphQL API queries
    op.add_column(
        "tb_asset_registry",
        sa.Column(
            "query_http",
            postgresql.JSONB(),
            nullable=True,
        ),
    )

    # Update query_metadata for existing query assets to include source_ref
    # This sets source_ref to the asset name and source_type to 'postgresql'
    op.execute("""
        UPDATE tb_asset_registry
        SET query_metadata = COALESCE(query_metadata, '{}'::jsonb) || jsonb_build_object(
            'source_ref', name,
            'source_type', 'postgresql'
        )
        WHERE asset_type = 'query' AND query_metadata IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column("tb_asset_registry", "query_http")
    op.drop_column("tb_asset_registry", "query_cypher")

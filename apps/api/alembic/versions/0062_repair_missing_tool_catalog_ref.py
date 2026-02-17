"""Repair missing tool_catalog_ref on tb_asset_registry

Revision ID: 0062_repair_missing_tool_catalog_ref
Revises: 0061_add_document_category_and_tags
Create Date: 2026-02-16 23:55:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0062_repair_missing_tool_catalog_ref"
down_revision = "0061_add_document_category_and_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guarded DDL for drifted environments where this column was never created.
    op.execute(
        """
        ALTER TABLE tb_asset_registry
        ADD COLUMN IF NOT EXISTS tool_catalog_ref VARCHAR(255)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE tb_asset_registry
        DROP COLUMN IF EXISTS tool_catalog_ref
        """
    )

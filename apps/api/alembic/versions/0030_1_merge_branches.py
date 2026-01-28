"""Merge two 0030 branch migrations

Revision ID: 0030_1_merge_branches
Revises: 0030_add_regression_rule_config, 0030_add_tool_asset_fields
Create Date: 2026-01-28 23:50:00.000000

"""

# revision identifiers, used by Alembic.
revision = "0030_1_merge_branches"
down_revision = ("0030_add_regression_rule_config", "0030_add_tool_asset_fields")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op merge migration"""
    pass


def downgrade() -> None:
    """No-op merge migration"""
    pass

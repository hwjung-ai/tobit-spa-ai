"""Add TbRegressionRuleConfig table for customizable regression judgment rules

Revision ID: 0030_add_regression_rule_config
Revises: 0029_add_screen_asset_fields
Create Date: 2026-01-18 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "0031_add_regression_rule_config"
down_revision = "0030_add_regression_rule_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create TbRegressionRuleConfig table with customizable judgment rules"""
    op.create_table(
        "tb_regression_rule_config",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("golden_query_id", sa.Text(), nullable=False, index=True),
        # FAIL thresholds
        sa.Column(
            "max_assets_changed", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "plan_intent_change_allowed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "tool_calls_failed_threshold",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "blocks_structure_variance_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
        # WARN thresholds
        sa.Column(
            "tool_calls_added_threshold",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "references_variance_threshold",
            sa.Float(),
            nullable=False,
            server_default="0.25",
        ),
        sa.Column(
            "tool_duration_spike_factor",
            sa.Float(),
            nullable=False,
            server_default="2.0",
        ),
        # Enable/disable rules
        sa.Column(
            "check_assets_changed", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "check_plan_intent", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "check_tool_errors", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "check_block_structure", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "check_tool_duration", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "check_references_variance",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        # Audit fields
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        sa.Column("updated_by", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index on golden_query_id for fast lookups
    op.create_index(
        "ix_regression_rule_config_golden_query_id",
        "tb_regression_rule_config",
        ["golden_query_id"],
    )


def downgrade() -> None:
    """Drop TbRegressionRuleConfig table"""
    op.drop_index(
        "ix_regression_rule_config_golden_query_id",
        table_name="tb_regression_rule_config",
    )
    op.drop_table("tb_regression_rule_config")

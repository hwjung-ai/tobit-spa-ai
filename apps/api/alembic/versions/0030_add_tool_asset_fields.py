"""
add tool asset fields to asset registry

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0030_add_tool_asset_fields"
down_revision = "0029_add_screen_asset_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tb_asset_registry", sa.Column("tool_type", sa.Text(), nullable=True))
    op.add_column(
        "tb_asset_registry",
        sa.Column("tool_config", sa.JSON(), nullable=True),
    )
    op.add_column(
        "tb_asset_registry",
        sa.Column("tool_input_schema", sa.JSON(), nullable=True),
    )
    op.add_column(
        "tb_asset_registry",
        sa.Column("tool_output_schema", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("tb_asset_registry", "tool_output_schema")
    op.drop_column("tb_asset_registry", "tool_input_schema")
    op.drop_column("tb_asset_registry", "tool_config")
    op.drop_column("tb_asset_registry", "tool_type")

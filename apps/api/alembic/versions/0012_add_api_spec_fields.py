"""add api spec fields

Revision ID: 0012_add_api_spec_fields
Revises: 0011_add_api_exec_log
Create Date: 2025-12-31 15:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0012_add_api_spec_fields"
down_revision = "0011_add_api_exec_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tb_api_def",
        sa.Column(
            "param_schema",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "tb_api_def",
        sa.Column(
            "runtime_policy",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "tb_api_def",
        sa.Column(
            "logic_spec",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tb_api_def", "logic_spec")
    op.drop_column("tb_api_def", "runtime_policy")
    op.drop_column("tb_api_def", "param_schema")

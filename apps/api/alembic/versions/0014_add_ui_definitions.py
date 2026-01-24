"""create tb_ui_def table and seed sample UI definitions

Revision ID: 0014_add_ui_definitions
Revises: 0013_add_api_exec_step_log
Create Date: 2025-12-31 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0014_add_ui_definitions"
down_revision = "0013_add_api_exec_step_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_ui_def",
        sa.Column(
            "ui_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("ui_name", sa.Text(), nullable=False),
        sa.Column("ui_type", sa.Text(), nullable=False),
        sa.Column(
            "schema",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("tb_ui_def")

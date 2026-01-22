"""create tb_api_exec_log table

Revision ID: 0011_add_api_exec_log
Revises: 0010_create_tb_api_def
Create Date: 2025-12-31 01:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0011_add_api_exec_log"
down_revision = "0010_create_tb_api_def"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_api_exec_log",
        sa.Column("exec_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("api_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("executed_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("executed_by", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("request_params", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tb_api_exec_log_api",
        "tb_api_exec_log",
        "tb_api_def",
        ["api_id"],
        ["api_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tb_api_exec_log_api", "tb_api_exec_log", type_="foreignkey")
    op.drop_table("tb_api_exec_log")

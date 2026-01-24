"""Add workflow step execution log table for API Manager."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0013_add_api_exec_step_log"
down_revision = "0012_add_api_spec_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_api_exec_step_log",
        sa.Column(
            "exec_step_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "exec_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tb_api_exec_log.exec_id"),
            nullable=False,
        ),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("node_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "duration_ms", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "row_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("references", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tb_api_exec_step_log")

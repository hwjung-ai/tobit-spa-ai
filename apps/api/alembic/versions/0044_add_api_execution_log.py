"""add api_execution_log table

Revision ID: 0044_add_api_execution_log
Revises: 0043_add_cep_performance_indexes
Create Date: 2026-02-06 01:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0044_add_api_execution_log"
down_revision = "0043_add_cep_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_execution_logs",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "api_id", postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column(
            "executed_by",
            sa.Text(),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "execution_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            index=True,
        ),
        sa.Column(
            "duration_ms", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "request_params", postgresql.JSONB(), nullable=True
        ),
        sa.Column(
            "response_data", postgresql.JSONB(), nullable=True
        ),
        sa.Column(
            "response_status", sa.Text(), nullable=False, server_default="success", index=True
        ),
        sa.Column(
            "error_message", sa.Text(), nullable=True
        ),
        sa.Column(
            "error_stacktrace", sa.Text(), nullable=True
        ),
        sa.Column(
            "rows_affected", sa.Integer(), nullable=True
        ),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=True
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_foreign_key(
        "fk_api_execution_logs_api_id",
        "api_execution_logs",
        "api_definitions",
        ["api_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_api_execution_logs_api_id",
        "api_execution_logs",
        type_="foreignkey"
    )
    op.drop_table("api_execution_logs")

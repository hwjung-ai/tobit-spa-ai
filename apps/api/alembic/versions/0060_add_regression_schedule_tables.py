"""Add regression schedule tables for persistence

Revision ID: 0060
Revises:
Create Date: 2026-02-14

Ensures regression schedules survive server restarts.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0060_add_regression_schedule"
down_revision = None  # Will be set by merge
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tb_regression_schedule table
    op.create_table(
        "tb_regression_schedule",
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("schedule_type", sa.Text(), nullable=False),
        sa.Column("cron_expression", sa.Text(), nullable=True),
        sa.Column("interval_minutes", sa.Integer(), nullable=True),
        sa.Column("test_suite_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("notify_on_failure", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_success", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notification_channels", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("tenant_id", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_regression_schedule_tenant_id", "tb_regression_schedule", ["tenant_id"])
    op.create_index("ix_regression_schedule_enabled", "tb_regression_schedule", ["enabled"])

    # Create tb_regression_schedule_run table
    op.create_table(
        "tb_regression_schedule_run",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("total_tests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("tenant_id", sa.Text(), nullable=True),
    )

    op.create_index("ix_regression_schedule_run_schedule_id", "tb_regression_schedule_run", ["schedule_id"])
    op.create_index("ix_regression_schedule_run_started_at", "tb_regression_schedule_run", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_regression_schedule_run_started_at", "tb_regression_schedule_run")
    op.drop_index("ix_regression_schedule_run_schedule_id", "tb_regression_schedule_run")
    op.drop_table("tb_regression_schedule_run")

    op.drop_index("ix_regression_schedule_enabled", "tb_regression_schedule")
    op.drop_index("ix_regression_schedule_tenant_id", "tb_regression_schedule")
    op.drop_table("tb_regression_schedule")

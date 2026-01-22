"""
add metric poll snapshot table

Revision ID: 0017_add_metric_poll_snapshot
Revises: 0016_add_cep_scheduler_state
Create Date: 2025-12-31 23:30:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0017_add_metric_poll_snapshot"
down_revision = "0016_add_cep_scheduler_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "tb_cep_metric_poll_snapshot",
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("instance_id", sa.Text(), nullable=False),
        sa.Column("is_leader", sa.Boolean(), nullable=False),
        sa.Column(
            "tick_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("tick_duration_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rule_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("evaluated_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("matched_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "recent_matches",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "recent_failures",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_tb_cep_metric_poll_snapshot_tick_at",
        "tb_cep_metric_poll_snapshot",
        [sa.text("tick_at DESC")],
    )
    op.create_index(
        "ix_tb_cep_metric_poll_snapshot_instance_id",
        "tb_cep_metric_poll_snapshot",
        ["instance_id"],
    )
    op.create_index(
        "ix_tb_cep_metric_poll_snapshot_is_leader",
        "tb_cep_metric_poll_snapshot",
        ["is_leader"],
    )


def downgrade() -> None:
    op.drop_index("ix_tb_cep_metric_poll_snapshot_is_leader", table_name="tb_cep_metric_poll_snapshot")
    op.drop_index("ix_tb_cep_metric_poll_snapshot_instance_id", table_name="tb_cep_metric_poll_snapshot")
    op.drop_index("ix_tb_cep_metric_poll_snapshot_tick_at", table_name="tb_cep_metric_poll_snapshot")
    op.drop_table("tb_cep_metric_poll_snapshot")

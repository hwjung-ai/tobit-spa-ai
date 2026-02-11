"""
add CEP performance indexes

Revision ID: 0043_add_cep_performance_indexes
Revises: 0042_add_trace_id_to_query_history
Create Date: 2026-02-06 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0043_add_cep_performance_indexes"
down_revision = "0042_add_trace_id_to_query_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================================================
    # tb_cep_rule indexes for better query performance
    # ========================================================================
    op.create_index(
        "ix_tb_cep_rule_rule_id",
        "tb_cep_rule",
        ["rule_id"],
    )
    op.create_index(
        "ix_tb_cep_rule_enabled",
        "tb_cep_rule",
        ["is_active"],
    )
    op.create_index(
        "ix_tb_cep_rule_created_at",
        "tb_cep_rule",
        [sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_tb_cep_rule_updated_at",
        "tb_cep_rule",
        [sa.text("updated_at DESC")],
    )
    op.create_index(
        "ix_tb_cep_rule_trigger_type",
        "tb_cep_rule",
        ["trigger_type"],
    )
    op.create_index(
        "ix_tb_cep_rule_active_updated",
        "tb_cep_rule",
        ["is_active", sa.text("updated_at DESC")],
    )

    # ========================================================================
    # tb_cep_notification_log indexes
    # ========================================================================
    op.create_index(
        "ix_tb_cep_notification_log_notification_id",
        "tb_cep_notification_log",
        ["notification_id"],
    )
    op.create_index(
        "ix_tb_cep_notification_log_fired_at",
        "tb_cep_notification_log",
        [sa.text("fired_at DESC")],
    )
    op.create_index(
        "ix_tb_cep_notification_log_status",
        "tb_cep_notification_log",
        ["status"],
    )
    op.create_index(
        "ix_tb_cep_notification_log_ack",
        "tb_cep_notification_log",
        ["ack"],
    )
    op.create_index(
        "ix_tb_cep_notification_log_fired_status",
        "tb_cep_notification_log",
        [sa.text("fired_at DESC"), "status"],
    )
    op.create_index(
        "ix_tb_cep_notification_log_notification_ack",
        "tb_cep_notification_log",
        ["notification_id", "ack"],
    )

    # ========================================================================
    # tb_cep_exec_log indexes
    # ========================================================================
    op.create_index(
        "ix_tb_cep_exec_log_rule_id",
        "tb_cep_exec_log",
        ["rule_id"],
    )
    op.create_index(
        "ix_tb_cep_exec_log_triggered_at",
        "tb_cep_exec_log",
        [sa.text("triggered_at DESC")],
    )
    op.create_index(
        "ix_tb_cep_exec_log_status",
        "tb_cep_exec_log",
        ["status"],
    )
    op.create_index(
        "ix_tb_cep_exec_log_rule_triggered",
        "tb_cep_exec_log",
        ["rule_id", sa.text("triggered_at DESC")],
    )

    # ========================================================================
    # tb_cep_metric_poll_snapshot indexes
    # ========================================================================
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

    # ========================================================================
    # tb_cep_notification indexes
    # ========================================================================
    op.create_index(
        "ix_tb_cep_notification_active",
        "tb_cep_notification",
        ["is_active"],
    )
    op.create_index(
        "ix_tb_cep_notification_channel",
        "tb_cep_notification",
        ["channel"],
    )
    op.create_index(
        "ix_tb_cep_notification_rule_id",
        "tb_cep_notification",
        ["rule_id"],
    )
    op.create_index(
        "ix_tb_cep_notification_active_created",
        "tb_cep_notification",
        ["is_active", sa.text("created_at DESC")],
    )

    # ========================================================================
    # tb_cep_scheduler_state indexes (if not already present)
    # ========================================================================
    op.create_index(
        "ix_tb_cep_scheduler_state_instance_id",
        "tb_cep_scheduler_state",
        ["instance_id"],
    )


def downgrade() -> None:
    # Drop all indexes in reverse order
    op.drop_index("ix_tb_cep_scheduler_state_instance_id", table_name="tb_cep_scheduler_state")
    op.drop_index("ix_tb_cep_notification_active_created", table_name="tb_cep_notification")
    op.drop_index("ix_tb_cep_notification_rule_id", table_name="tb_cep_notification")
    op.drop_index("ix_tb_cep_notification_channel", table_name="tb_cep_notification")
    op.drop_index("ix_tb_cep_notification_active", table_name="tb_cep_notification")
    op.drop_index("ix_tb_cep_metric_poll_snapshot_is_leader", table_name="tb_cep_metric_poll_snapshot")
    op.drop_index("ix_tb_cep_metric_poll_snapshot_instance_id", table_name="tb_cep_metric_poll_snapshot")
    op.drop_index("ix_tb_cep_metric_poll_snapshot_tick_at", table_name="tb_cep_metric_poll_snapshot")
    op.drop_index("ix_tb_cep_exec_log_rule_triggered", table_name="tb_cep_exec_log")
    op.drop_index("ix_tb_cep_exec_log_status", table_name="tb_cep_exec_log")
    op.drop_index("ix_tb_cep_exec_log_triggered_at", table_name="tb_cep_exec_log")
    op.drop_index("ix_tb_cep_exec_log_rule_id", table_name="tb_cep_exec_log")
    op.drop_index("ix_tb_cep_notification_log_notification_ack", table_name="tb_cep_notification_log")
    op.drop_index("ix_tb_cep_notification_log_fired_status", table_name="tb_cep_notification_log")
    op.drop_index("ix_tb_cep_notification_log_ack", table_name="tb_cep_notification_log")
    op.drop_index("ix_tb_cep_notification_log_status", table_name="tb_cep_notification_log")
    op.drop_index("ix_tb_cep_notification_log_fired_at", table_name="tb_cep_notification_log")
    op.drop_index("ix_tb_cep_notification_log_notification_id", table_name="tb_cep_notification_log")
    op.drop_index("ix_tb_cep_rule_active_updated", table_name="tb_cep_rule")
    op.drop_index("ix_tb_cep_rule_trigger_type", table_name="tb_cep_rule")
    op.drop_index("ix_tb_cep_rule_updated_at", table_name="tb_cep_rule")
    op.drop_index("ix_tb_cep_rule_created_at", table_name="tb_cep_rule")
    op.drop_index("ix_tb_cep_rule_enabled", table_name="tb_cep_rule")
    op.drop_index("ix_tb_cep_rule_rule_id", table_name="tb_cep_rule")

"""
add cep notifications tables

Revision ID: 0018_add_cep_notifications
Revises: 0017_add_metric_poll_snapshot
Create Date: 2025-12-31 23:50:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0018_add_cep_notifications"
down_revision = "0017_add_cep_scheduler_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "tb_cep_notification",
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=False),
        sa.Column(
            "headers",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "trigger",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "policy",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
    op.create_index(
        "ix_tb_cep_notification_is_active",
        "tb_cep_notification",
        ["is_active"],
    )

    op.create_table(
        "tb_cep_notification_log",
        sa.Column(
            "log_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tb_cep_notification.notification_id"),
            nullable=False,
        ),
        sa.Column(
            "fired_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("dedup_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_tb_cep_notification_log_notification_id_fired_at",
        "tb_cep_notification_log",
        ["notification_id", sa.text("fired_at DESC")],
    )
    op.create_index(
        "ix_tb_cep_notification_log_fired_at",
        "tb_cep_notification_log",
        [sa.text("fired_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cep_notification_log_fired_at", table_name="tb_cep_notification_log"
    )
    op.drop_index(
        "ix_tb_cep_notification_log_notification_id_fired_at",
        table_name="tb_cep_notification_log",
    )
    op.drop_table("tb_cep_notification_log")
    op.drop_index("ix_tb_cep_notification_is_active", table_name="tb_cep_notification")
    op.drop_table("tb_cep_notification")

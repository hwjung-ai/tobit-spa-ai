"""
add cep event ack fields

Revision ID: 0019_add_cep_event_ack_fields
Revises: 0018_add_cep_notifications
Create Date: 2026-01-01 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0019_add_cep_event_ack_fields"
down_revision = "0018_add_cep_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tb_cep_notification",
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tb_cep_notification_log",
        sa.Column("ack", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "tb_cep_notification_log",
        sa.Column("ack_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "tb_cep_notification_log",
        sa.Column("ack_by", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tb_cep_notification_log", "ack_by")
    op.drop_column("tb_cep_notification_log", "ack_at")
    op.drop_column("tb_cep_notification_log", "ack")
    op.drop_column("tb_cep_notification", "rule_id")

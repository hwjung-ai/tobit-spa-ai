"""
create cep builder tables

Revision ID: 0015_add_cep_tables
Revises: 0014_add_ui_definitions
Create Date: 2025-12-31 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0015_add_cep_tables"
down_revision = "0014_add_ui_definitions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "tb_cep_rule",
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("rule_name", sa.Text(), nullable=False),
        sa.Column("trigger_type", sa.Text(), nullable=False),
        sa.Column(
            "trigger_spec",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "action_spec",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
    op.create_index("ix_tb_cep_rule_is_active", "tb_cep_rule", ["is_active"])

    op.create_table(
        "tb_cep_exec_log",
        sa.Column(
            "exec_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "triggered_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "references",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index(
        "ix_tb_cep_exec_log_rule_id_triggered_at",
        "tb_cep_exec_log",
        ["rule_id", sa.text("triggered_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_tb_cep_exec_log_rule_id_triggered_at", table_name="tb_cep_exec_log")
    op.drop_table("tb_cep_exec_log")
    op.drop_index("ix_tb_cep_rule_is_active", table_name="tb_cep_rule")
    op.drop_table("tb_cep_rule")

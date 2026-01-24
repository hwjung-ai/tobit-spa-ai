"""
create cep scheduler state table

Revision ID: 0016_add_cep_scheduler_state
Revises: 0015_add_cep_tables
Create Date: 2025-12-31 22:45:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0016_add_cep_scheduler_state"
down_revision = "0015_add_cep_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "tb_cep_scheduler_state",
        sa.Column(
            "state_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("instance_id", sa.Text(), nullable=False),
        sa.Column(
            "is_leader", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "last_heartbeat_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "started_at",
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
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_tb_cep_scheduler_state_instance", "tb_cep_scheduler_state", ["instance_id"]
    )
    op.create_index(
        "ix_tb_cep_scheduler_state_is_leader", "tb_cep_scheduler_state", ["is_leader"]
    )
    op.create_index(
        "ix_tb_cep_scheduler_state_updated_at",
        "tb_cep_scheduler_state",
        [sa.text("updated_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cep_scheduler_state_updated_at", table_name="tb_cep_scheduler_state"
    )
    op.drop_index(
        "ix_tb_cep_scheduler_state_is_leader", table_name="tb_cep_scheduler_state"
    )
    op.drop_constraint(
        "uq_tb_cep_scheduler_state_instance", "tb_cep_scheduler_state", type_="unique"
    )
    op.drop_table("tb_cep_scheduler_state")

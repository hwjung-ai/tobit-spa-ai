"""create ops history tables

Revision ID: 0009_add_ops_history
Revises: 0008_add_ops_events
Create Date: 2025-12-30 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0009_add_ops_history"
down_revision = "0008_add_ops_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'t1'"),
        ),
        sa.Column(
            "ci_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("ci.ci_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("maint_type", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("performer", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "work_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'t1'"),
        ),
        sa.Column(
            "ci_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("ci.ci_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("work_type", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("impact_level", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("work_history")
    op.drop_table("maintenance_history")

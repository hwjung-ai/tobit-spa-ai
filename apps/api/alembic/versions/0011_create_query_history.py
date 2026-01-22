"""create query history table

Revision ID: 0011_create_query_history
Revises: 0010_create_tb_api_def
Create Date: 2026-01-03 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0011_create_query_history"
down_revision = "0010_create_tb_api_def"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False, server_default=sa.text("'default'")),
        sa.Column("user_id", sa.Text(), nullable=False, server_default=sa.text("'default'")),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'ok'")),
        sa.Column("response", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("query_history")

"""add runtime_policy to api_definitions and extend apimode enum

Revision ID: 0049_add_api_definitions_runtime_policy
Revises: 0048_add_p0_p1_foundation_tables
Create Date: 2026-02-08 13:45:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0049_add_api_definitions_runtime_policy"
down_revision = "0048_add_p0_p1_foundation_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("api_definitions")}

    if "runtime_policy" not in columns:
        op.add_column(
            "api_definitions",
            sa.Column(
                "runtime_policy",
                postgresql.JSON(),
                nullable=False,
                server_default=sa.text("'{}'::json"),
            ),
        )

    # Expand legacy enum for current ApiMode values.
    op.execute("ALTER TYPE apimode ADD VALUE IF NOT EXISTS 'http'")
    op.execute("ALTER TYPE apimode ADD VALUE IF NOT EXISTS 'script'")


def downgrade() -> None:
    # Enum value removal is intentionally skipped (unsafe in PostgreSQL).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("api_definitions")}
    if "runtime_policy" in columns:
        op.drop_column("api_definitions", "runtime_policy")

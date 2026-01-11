"""create api definitions table

Revision ID: 0005_add_api_definitions
Revises: 0004_add_documents
Create Date: 2025-12-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_add_api_definitions"
down_revision = "0004_add_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("scope", sa.Enum("system", "custom", name="apiscope"), nullable=False, server_default="custom"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("mode", sa.Enum("sql", "python", "workflow", name="apimode"), nullable=True),
        sa.Column("logic", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("method", "path", name="uq_api_method_path"),
    )


def downgrade() -> None:
    op.drop_table("api_definitions")
    op.execute("DROP TYPE IF EXISTS apiscope")
    op.execute("DROP TYPE IF EXISTS apimode")

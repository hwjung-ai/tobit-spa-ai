"""create ops ci tables

Revision ID: 0006_add_ops_ci
Revises: 0005_add_api_definitions
Create Date: 2025-12-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006_add_ops_ci"
down_revision = "0005_add_api_definitions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ci",
        sa.Column(
            "ci_id",
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
            "ci_type",
            sa.Enum("SYSTEM", "HW", "SW", name="ci_type"),
            nullable=False,
        ),
        sa.Column(
            "ci_subtype",
            sa.Enum(
                "business_system",
                "control_system",
                "monitoring_system",
                "server",
                "network",
                "storage",
                "security",
                "os",
                "db",
                "was",
                "web",
                "app",
                name="ci_subtype",
            ),
            nullable=False,
        ),
        sa.Column("ci_code", sa.Text(), nullable=False, unique=True),
        sa.Column("ci_name", sa.Text(), nullable=False),
        sa.Column("ci_category", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("criticality", sa.Integer(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            """(
                ci_type = 'SYSTEM' AND ci_subtype IN ('business_system', 'control_system', 'monitoring_system')
            ) OR (
                ci_type = 'HW' AND ci_subtype IN ('server', 'network', 'storage', 'security')
            ) OR (
                ci_type = 'SW' AND ci_subtype IN ('os', 'db', 'was', 'web', 'app')
            )""",
            name="ck_ci_type_subtype",
        ),
    )

    op.create_table(
        "ci_ext",
        sa.Column(
            "ci_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("ci.ci_id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("ci_ext")
    op.drop_table("ci")
    op.execute("DROP TYPE IF EXISTS ci_subtype")
    op.execute("DROP TYPE IF EXISTS ci_type")

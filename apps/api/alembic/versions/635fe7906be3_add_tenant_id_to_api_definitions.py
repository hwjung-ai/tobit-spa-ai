import sqlalchemy as sa
from alembic import op

revision = "635fe7906be3"
down_revision = '0059_merge_heads'
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "api_definitions", "tenant_id"):
        op.add_column("api_definitions", sa.Column("tenant_id", sa.Text(), nullable=True))

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "api_definitions", "ix_api_definitions_tenant_id"):
        op.create_index(
            "ix_api_definitions_tenant_id",
            "api_definitions",
            ["tenant_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "api_definitions", "ix_api_definitions_tenant_id"):
        op.drop_index("ix_api_definitions_tenant_id", table_name="api_definitions")

    inspector = sa.inspect(bind)
    if _has_column(inspector, "api_definitions", "tenant_id"):
        op.drop_column("api_definitions", "tenant_id")

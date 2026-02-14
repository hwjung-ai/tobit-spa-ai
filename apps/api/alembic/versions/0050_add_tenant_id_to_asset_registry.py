"""Add tenant_id to tb_asset_registry for multi-tenant isolation.

Revision ID: 0057_add_tenant_id_to_asset_registry
Revises: 0056
"""

import sqlalchemy as sa
from alembic import op

revision = "0057_add_tenant_id_to_asset_registry"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tb_asset_registry")}
    indexes = {idx["name"] for idx in inspector.get_indexes("tb_asset_registry")}

    if "tenant_id" not in columns:
        op.add_column(
            "tb_asset_registry",
            sa.Column(
                "tenant_id",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'default'"),
            ),
        )
    else:
        bind.execute(
            sa.text(
                "UPDATE tb_asset_registry SET tenant_id = 'default' WHERE tenant_id IS NULL"
            )
        )
        op.alter_column(
            "tb_asset_registry",
            "tenant_id",
            existing_type=sa.Text(),
            nullable=False,
            server_default=sa.text("'default'"),
        )

    if "ix_tb_asset_registry_tenant_id" not in indexes:
        op.create_index(
            "ix_tb_asset_registry_tenant_id",
            "tb_asset_registry",
            ["tenant_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tb_asset_registry")}
    indexes = {idx["name"] for idx in inspector.get_indexes("tb_asset_registry")}

    if "ix_tb_asset_registry_tenant_id" in indexes:
        op.drop_index("ix_tb_asset_registry_tenant_id", table_name="tb_asset_registry")
    if "tenant_id" in columns:
        op.drop_column("tb_asset_registry", "tenant_id")

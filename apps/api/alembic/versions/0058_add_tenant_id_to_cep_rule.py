"""Add tenant_id to tb_cep_rule for tenant-aware CEP queries.

Revision ID: 0058_add_tenant_id_to_cep_rule
Revises: 0057_add_tenant_id_to_asset_registry
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0058_add_tenant_id_to_cep_rule"
down_revision = "0057_add_tenant_id_to_asset_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tb_cep_rule")}
    indexes = {idx["name"] for idx in inspector.get_indexes("tb_cep_rule")}

    if "tenant_id" not in columns:
        op.add_column(
            "tb_cep_rule",
            sa.Column(
                "tenant_id",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'default'"),
            ),
        )
    else:
        bind.execute(
            sa.text("UPDATE tb_cep_rule SET tenant_id = 'default' WHERE tenant_id IS NULL")
        )
        op.alter_column(
            "tb_cep_rule",
            "tenant_id",
            existing_type=sa.Text(),
            nullable=False,
            server_default=sa.text("'default'"),
        )

    if "ix_tb_cep_rule_tenant_id" not in indexes:
        op.create_index(
            "ix_tb_cep_rule_tenant_id",
            "tb_cep_rule",
            ["tenant_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tb_cep_rule")}
    indexes = {idx["name"] for idx in inspector.get_indexes("tb_cep_rule")}

    if "ix_tb_cep_rule_tenant_id" in indexes:
        op.drop_index("ix_tb_cep_rule_tenant_id", table_name="tb_cep_rule")
    if "tenant_id" in columns:
        op.drop_column("tb_cep_rule", "tenant_id")

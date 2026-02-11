"""normalize_default_tenant_alias

Revision ID: 0056
Revises: 0055
Create Date: 2026-02-11 19:25:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0056"
down_revision: Union[str, None] = "0055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_ALIAS = "default-tenant"
DEFAULT_TENANT = "default"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names(schema="public")


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(
        col["name"] == column_name
        for col in inspector.get_columns(table_name, schema="public")
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in inspector.get_table_names(schema="public"):
        if not _table_exists(inspector, table_name):
            continue
        if not _has_column(inspector, table_name, "tenant_id"):
            continue
        bind.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                SET tenant_id = :default_tenant
                WHERE tenant_id = :legacy_alias
                """
            ),
            {
                "default_tenant": DEFAULT_TENANT,
                "legacy_alias": LEGACY_ALIAS,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in inspector.get_table_names(schema="public"):
        if not _table_exists(inspector, table_name):
            continue
        if not _has_column(inspector, table_name, "tenant_id"):
            continue
        bind.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                SET tenant_id = :legacy_alias
                WHERE tenant_id = :default_tenant
                """
            ),
            {
                "default_tenant": DEFAULT_TENANT,
                "legacy_alias": LEGACY_ALIAS,
            },
        )

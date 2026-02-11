"""normalize_default_tenant

Revision ID: 0054
Revises: 0053
Create Date: 2026-02-11 15:40:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0054"
down_revision: Union[str, None] = "0053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_TENANT = "t1"
DEFAULT_TENANT = "default"

TENANT_TABLES = [
    "tb_user",
    "chat_thread",
    "documents",
    "document_search_log",
    "ci",
    "event_log",
    "maintenance_history",
    "metric_value",
    "query_history",
    "uploads",
    "work_history",
]

TENANT_DEFAULT_TABLES = [
    "ci",
    "event_log",
    "maintenance_history",
    "metric_value",
    "work_history",
]


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names(schema="public")


def _has_tenant_column(inspector: sa.Inspector, table_name: str) -> bool:
    return any(
        col["name"] == "tenant_id"
        for col in inspector.get_columns(table_name, schema="public")
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Normalize existing data from legacy tenant "t1" to "default"
    for table_name in TENANT_TABLES:
        if not _table_exists(inspector, table_name):
            continue
        if not _has_tenant_column(inspector, table_name):
            continue
        bind.execute(
            sa.text(
                f"UPDATE {table_name} SET tenant_id = :new_tenant WHERE tenant_id = :old_tenant"
            ),
            {"new_tenant": DEFAULT_TENANT, "old_tenant": LEGACY_TENANT},
        )

    # 2) Change DB default tenant for legacy tables that still had 't1' default
    for table_name in TENANT_DEFAULT_TABLES:
        if not _table_exists(inspector, table_name):
            continue
        if not _has_tenant_column(inspector, table_name):
            continue
        bind.execute(
            sa.text(
                f"ALTER TABLE {table_name} ALTER COLUMN tenant_id SET DEFAULT '{DEFAULT_TENANT}'"
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in TENANT_TABLES:
        if not _table_exists(inspector, table_name):
            continue
        if not _has_tenant_column(inspector, table_name):
            continue
        bind.execute(
            sa.text(
                f"UPDATE {table_name} SET tenant_id = :old_tenant WHERE tenant_id = :new_tenant"
            ),
            {"new_tenant": DEFAULT_TENANT, "old_tenant": LEGACY_TENANT},
        )

    for table_name in TENANT_DEFAULT_TABLES:
        if not _table_exists(inspector, table_name):
            continue
        if not _has_tenant_column(inspector, table_name):
            continue
        bind.execute(
            sa.text(
                f"ALTER TABLE {table_name} ALTER COLUMN tenant_id SET DEFAULT '{LEGACY_TENANT}'"
            ),
        )

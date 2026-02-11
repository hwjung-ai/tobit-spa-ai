"""normalize_default_user_history

Revision ID: 0055
Revises: 0054
Create Date: 2026-02-11 15:55:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0055"
down_revision: Union[str, None] = "0054"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_USERNAME = "admin@tobit.local"
DEFAULT_TENANT = "default"
LEGACY_USER_IDS = ("default", "dev-user", "test-user", "test_user")
TARGET_TABLES = ("chat_thread", "documents", "query_history")


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

    if not _table_exists(inspector, "tb_user"):
        return

    admin_user_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM tb_user
            WHERE username = :username
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"username": ADMIN_USERNAME},
    ).scalar()

    if not admin_user_id:
        return

    for table_name in TARGET_TABLES:
        if not _table_exists(inspector, table_name):
            continue
        if not (_has_column(inspector, table_name, "tenant_id") and _has_column(inspector, table_name, "user_id")):
            continue
        bind.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                SET user_id = :admin_user_id
                WHERE tenant_id = :tenant_id
                  AND user_id = ANY(:legacy_user_ids)
                """
            ),
            {
                "admin_user_id": str(admin_user_id),
                "tenant_id": DEFAULT_TENANT,
                "legacy_user_ids": list(LEGACY_USER_IDS),
            },
        )


def downgrade() -> None:
    # Irreversible data normalization (no-op downgrade)
    pass

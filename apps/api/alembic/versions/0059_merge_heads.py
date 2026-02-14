"""Merge Alembic heads into a single linear head.

Revision ID: 0059_merge_heads
Revises: 0058_add_tenant_id_to_cep_rule, 0049_add_ml_models_table, 0049_add_screen_editor
Create Date: 2026-02-14
"""

from typing import Sequence, Union

revision: str = "0059_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0058_add_tenant_id_to_cep_rule",
    "0049_add_ml_models_table",
    "0049_add_screen_editor",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge-only revision: no schema changes.
    pass


def downgrade() -> None:
    # Merge-only revision: no schema changes.
    pass

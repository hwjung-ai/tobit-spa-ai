"""add_api_auth_policy_fields

Revision ID: 0053
Revises: 0052
Create Date: 2026-02-11 20:10:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0053"
down_revision: Union[str, None] = "0052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_definitions",
        sa.Column(
            "auth_mode",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'jwt_only'"),
        ),
    )
    op.add_column(
        "api_definitions",
        sa.Column(
            "required_scopes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )

    # Optional compatibility for legacy table if present.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tb_api_def" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("tb_api_def")}
        if "auth_mode" not in cols:
            op.add_column(
                "tb_api_def",
                sa.Column(
                    "auth_mode",
                    sa.Text(),
                    nullable=False,
                    server_default=sa.text("'jwt_only'"),
                ),
            )
        if "required_scopes" not in cols:
            op.add_column(
                "tb_api_def",
                sa.Column(
                    "required_scopes",
                    sa.JSON(),
                    nullable=False,
                    server_default=sa.text("'[]'::json"),
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tb_api_def" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("tb_api_def")}
        if "required_scopes" in cols:
            op.drop_column("tb_api_def", "required_scopes")
        if "auth_mode" in cols:
            op.drop_column("tb_api_def", "auth_mode")

    op.drop_column("api_definitions", "required_scopes")
    op.drop_column("api_definitions", "auth_mode")


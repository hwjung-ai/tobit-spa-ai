"""merge history and cep heads

Revision ID: 0020_merge_history_and_cep_heads
Revises: 0011_create_query_history, 0019_add_cep_event_ack_fields
Create Date: 2026-01-03 12:34:00.000000
"""


# revision identifiers, used by Alembic.
revision = "0020_merge_history_and_cep_heads"
down_revision = ("0011_create_query_history", "0019_add_cep_event_ack_fields")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

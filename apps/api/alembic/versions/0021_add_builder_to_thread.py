"""add builder column to chat_thread"""

from alembic import op
import sqlalchemy as sa

revision = "0021_add_builder_to_thread"
down_revision = "0020_merge_history_and_cep_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_thread", sa.Column("builder", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_thread", "builder")

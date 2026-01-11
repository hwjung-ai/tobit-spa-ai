"""add title_finalized flag to chat_thread"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_thread_title_finalized"
down_revision = "0002_add_thread_summary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_thread", sa.Column("title_finalized", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("chat_thread", "title_finalized", server_default=None)


def downgrade() -> None:
    op.drop_column("chat_thread", "title_finalized")

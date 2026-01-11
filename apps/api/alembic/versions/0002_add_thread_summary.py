"""add summary column to chat_thread"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_thread_summary"
down_revision = "0001_create_threads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_thread", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_thread", "summary")

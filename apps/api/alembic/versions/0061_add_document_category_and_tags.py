"""Add document category and tags fields

Revision ID: 0061_add_document_category_and_tags
Revises: 0060_add_regression_schedule
Create Date: 2026-02-15 20:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0061_add_document_category_and_tags'
down_revision = '0060_add_regression_schedule'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add category column to documents table
    op.add_column(
        'documents',
        sa.Column('category', sa.String(length=50), nullable=True, server_default='other')
    )

    # Add tags column to documents table (JSON type)
    op.add_column(
        'documents',
        sa.Column('tags', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    # Remove tags column
    op.drop_column('documents', 'tags')

    # Remove category column
    op.drop_column('documents', 'category')

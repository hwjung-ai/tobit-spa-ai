"""Enhance document tables with multi-format support and advanced search"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0036_enhance_document_tables"
down_revision = "0035_add_ci_management_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enhance document-related tables."""

    # Add new columns to documents table
    op.add_column('documents', sa.Column('format', sa.String(20), nullable=True, default='pdf'))
    op.add_column('documents', sa.Column('processing_progress', sa.Integer(), nullable=True, default=0))
    op.add_column('documents', sa.Column('total_chunks', sa.Integer(), nullable=True, default=0))
    op.add_column('documents', sa.Column('error_details', JSONB(), nullable=True))
    op.add_column('documents', sa.Column('doc_metadata', JSONB(), nullable=True))
    op.add_column('documents', sa.Column('created_by', sa.String(36), nullable=True))

    # Create index for format
    op.create_index('ix_documents_format', 'documents', ['format'])

    # Enhance document_chunks table
    op.add_column('document_chunks', sa.Column('chunk_version', sa.Integer(), nullable=True, default=1))
    op.add_column('document_chunks', sa.Column('chunk_type', sa.String(50), nullable=True, default='text'))
    op.add_column('document_chunks', sa.Column('position_in_doc', sa.Integer(), nullable=True))
    op.add_column('document_chunks', sa.Column('page_number', sa.Integer(), nullable=True))
    op.add_column('document_chunks', sa.Column('slide_number', sa.Integer(), nullable=True))
    op.add_column('document_chunks', sa.Column('table_data', JSONB(), nullable=True))
    op.add_column('document_chunks', sa.Column('source_hash', sa.String(64), nullable=True))
    op.add_column('document_chunks', sa.Column('relevance_score', sa.Float(), nullable=True))

    # Create indexes for search
    op.create_index('ix_document_chunks_chunk_type', 'document_chunks', ['chunk_type'])
    op.create_index('ix_document_chunks_page_number', 'document_chunks', ['page_number'])

    # Create full-text search index on chunk text
    op.execute("""
        CREATE INDEX idx_document_chunk_text_search
        ON document_chunks
        USING GIN(to_tsvector('english', text))
    """)


def downgrade() -> None:
    """Rollback document table enhancements."""

    # Drop full-text search index
    op.drop_index('idx_document_chunk_text_search', 'document_chunks')

    # Drop new indexes
    op.drop_index('ix_document_chunks_page_number', 'document_chunks')
    op.drop_index('ix_document_chunks_chunk_type', 'document_chunks')
    op.drop_index('ix_documents_format', 'documents')

    # Drop columns from document_chunks
    op.drop_column('document_chunks', 'relevance_score')
    op.drop_column('document_chunks', 'source_hash')
    op.drop_column('document_chunks', 'table_data')
    op.drop_column('document_chunks', 'slide_number')
    op.drop_column('document_chunks', 'page_number')
    op.drop_column('document_chunks', 'position_in_doc')
    op.drop_column('document_chunks', 'chunk_type')
    op.drop_column('document_chunks', 'chunk_version')

    # Drop columns from documents
    op.drop_column('documents', 'created_by')
    op.drop_column('documents', 'doc_metadata')
    op.drop_column('documents', 'error_details')
    op.drop_column('documents', 'total_chunks')
    op.drop_column('documents', 'processing_progress')
    op.drop_column('documents', 'format')

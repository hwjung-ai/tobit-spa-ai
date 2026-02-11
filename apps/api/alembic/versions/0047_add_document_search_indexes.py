"""Add document search indexes for pgvector and BM25

Revision ID: 0045
Revises: 0044
Create Date: 2026-02-06 10:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0047_add_document_search_indexes"
down_revision = "0046_add_cep_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create indexes for document search optimization:
    1. Vector index (IVFFLAT) for pgvector similarity search
    2. GIN index (tsvector) for BM25 full-text search
    3. Composite indexes for tenant-based filtering
    """

    # Vector similarity index using IVFFLAT
    # This enables fast approximate nearest neighbor search on embeddings
    # Parameters:
    #   - lists=100: Number of clusters (good for ~1000 vectors per cluster)
    #   - vector_cosine_ops: Use cosine distance metric
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding
        ON document_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)
    print("✅ Created vector index: ix_document_chunks_embedding")

    # Full-text search index using GIN
    # This enables efficient BM25 searches via ts_rank
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_text_tsvector
        ON document_chunks USING GIN (to_tsvector('english', text));
    """)
    print("✅ Created text search index: ix_document_chunks_text_tsvector")

    # Composite index for tenant-based queries
    # Includes deleted_at filtering and creation date ordering
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_tenant_created
        ON document_chunks (document_id)
        INCLUDE (created_at);
    """)
    print("✅ Created composite index: ix_document_chunks_tenant_created")

    # Index for document filtering in search queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_tenant_deleted
        ON documents (tenant_id, deleted_at)
        INCLUDE (id, filename);
    """)
    print("✅ Created document filtering index: ix_documents_tenant_deleted")


def downgrade() -> None:
    """
    Remove all document search indexes
    """

    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding;")
    print("⬇️  Dropped vector index: ix_document_chunks_embedding")

    op.execute("DROP INDEX IF EXISTS ix_document_chunks_text_tsvector;")
    print("⬇️  Dropped text search index: ix_document_chunks_text_tsvector")

    op.execute("DROP INDEX IF EXISTS ix_document_chunks_tenant_created;")
    print("⬇️  Dropped composite index: ix_document_chunks_tenant_created")

    op.execute("DROP INDEX IF EXISTS ix_documents_tenant_deleted;")
    print("⬇️  Dropped document filtering index: ix_documents_tenant_deleted")

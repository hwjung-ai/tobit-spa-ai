"""Add document access control and search logging tables"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0037_add_document_access_and_search_tables"
down_revision = "0036_enhance_document_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create document access and search logging tables."""

    # Create document_access table
    op.create_table(
        "document_access",
        sa.Column("access_id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("role_id", sa.String(36), nullable=True),
        sa.Column(
            "access_type", sa.String(50), nullable=False
        ),  # read, download, share
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "granted_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_document_access_document_id", "document_access", ["document_id"]
    )
    op.create_index("ix_document_access_user_id", "document_access", ["user_id"])
    op.create_index("ix_document_access_expires_at", "document_access", ["expires_at"])

    # Create document_search_log table
    op.create_table(
        "document_search_log",
        sa.Column("search_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "search_type", sa.String(20), nullable=False
        ),  # text, semantic, hybrid
        sa.Column("filter_criteria", JSONB(), nullable=True),
        sa.Column("results_count", sa.Integer(), nullable=False, default=0),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_document_search_log_user_id", "document_search_log", ["user_id"]
    )
    op.create_index(
        "ix_document_search_log_tenant_id", "document_search_log", ["tenant_id"]
    )
    op.create_index(
        "ix_document_search_log_created_at", "document_search_log", ["created_at"]
    )

    # Create document_chunk_metadata table
    op.create_table(
        "document_chunk_metadata",
        sa.Column("metadata_id", sa.String(36), primary_key=True),
        sa.Column(
            "chunk_id",
            sa.String(36),
            sa.ForeignKey("document_chunks.id"),
            nullable=False,
        ),
        sa.Column("chunk_language", sa.String(20), nullable=True, default="en"),
        sa.Column("contains_tables", sa.Boolean(), nullable=False, default=False),
        sa.Column("contains_images", sa.Boolean(), nullable=False, default=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "extraction_method", sa.String(50), nullable=True
        ),  # pdf_text, ocr, etc.
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_document_chunk_metadata_chunk_id", "document_chunk_metadata", ["chunk_id"]
    )
    op.create_index(
        "ix_document_chunk_metadata_language",
        "document_chunk_metadata",
        ["chunk_language"],
    )


def downgrade() -> None:
    """Drop document access and search logging tables."""

    op.drop_index("ix_document_chunk_metadata_language", "document_chunk_metadata")
    op.drop_index("ix_document_chunk_metadata_chunk_id", "document_chunk_metadata")
    op.drop_table("document_chunk_metadata")

    op.drop_index("ix_document_search_log_created_at", "document_search_log")
    op.drop_index("ix_document_search_log_tenant_id", "document_search_log")
    op.drop_index("ix_document_search_log_user_id", "document_search_log")
    op.drop_table("document_search_log")

    op.drop_index("ix_document_access_expires_at", "document_access")
    op.drop_index("ix_document_access_user_id", "document_access")
    op.drop_index("ix_document_access_document_id", "document_access")
    op.drop_table("document_access")

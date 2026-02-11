#!/usr/bin/env python3
"""
Test document search directly using SQL query.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "apps/api"))
import sys

sys.path.append(str(project_root / "apps/api"))

from core.db import get_session
from sqlmodel import text


def test_document_search_sql():
    """Test document search using SQL"""

    session = next(get_session())

    try:
        # Test the document search query directly
        query = text("""
            SELECT
                d.id as document_id,
                d.filename as document_name,
                dc.chunk_id,
                dc.text as chunk_text,
                dc.page_number,
                'document' as chunk_type,
                0.8 as relevance_score
            FROM documents d
            JOIN document_chunks dc ON d.id = dc.document_id
            WHERE d.tenant_id = 'default'
            AND dc.text ILIKE '%아키텍처%'
            ORDER BY
                CASE
                    WHEN d.filename ILIKE '%아키텍처%' THEN 1
                    ELSE 2
                END,
                dc.page_number
            LIMIT 10
        """)

        result = session.exec(query).all()

        print(f"🔍 Found {len(result)} documents with '아키텍처':")

        for i, row in enumerate(result[:5], 1):
            print(f"\n{i}. Document: {row.document_name}")
            print(f"   Chunk ID: {row.chunk_id}")
            print(f"   Page: {row.page_number}")
            print(f"   Text: {row.chunk_text[:200]}...")
            print(f"   Score: {row.relevance_score}")

        # Try a different search term
        query2 = text("""
            SELECT
                d.id as document_id,
                d.filename as document_name,
                dc.chunk_id,
                dc.text as chunk_text,
                dc.page_number,
                'document' as chunk_type,
                0.8 as relevance_score
            FROM documents d
            JOIN document_chunks dc ON d.id = dc.document_id
            WHERE d.tenant_id = 'default'
            AND dc.text ILIKE '%시스템%'
            ORDER BY
                CASE
                    WHEN d.filename ILIKE '%시스템%' THEN 1
                    ELSE 2
                END,
                dc.page_number
            LIMIT 5
        """)

        result2 = session.exec(query2).all()

        print(f"\n🔍 Found {len(result2)} documents with '시스템':")

        for i, row in enumerate(result2, 1):
            print(f"\n{i}. Document: {row.document_name}")
            print(f"   Text: {row.chunk_text[:200]}...")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_document_search_sql()
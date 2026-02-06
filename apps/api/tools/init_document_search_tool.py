#!/usr/bin/env python3
"""
Initialize Document Search Tool Asset for OPS CI Integration

This script registers a Document Search Tool as an Asset in the Asset Registry,
allowing OPS CI Ask to use document search via DynamicTool with http_api type.

Usage:
    python tools/init_document_search_tool.py

Environment Variables:
    DATABASE_URL: SQLAlchemy database URL
    API_BASE_URL: Base URL for API endpoints (default: http://localhost:8000)
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import engine, get_session_context
from app.modules.asset_registry.crud import create_tool_asset, publish_asset
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import Session


DOCUMENT_SEARCH_TOOL_CONFIG = {
    "name": "document_search",
    "description": "Search documents using hybrid vector + BM25 search with pgvector embeddings",
    "tool_type": "http_api",
    "tool_config": {
        "url": "{API_BASE_URL}/api/documents/search",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "X-Tenant-Id": "{tenant_id}"
        },
        "body_template": {
            "query": "query",
            "search_type": "search_type",
            "top_k": "top_k",
            "min_relevance": "min_relevance"
        }
    },
    "tool_input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text (required)"
            },
            "search_type": {
                "type": "string",
                "enum": ["text", "vector", "hybrid"],
                "default": "hybrid",
                "description": "Search method: text (BM25), vector (semantic), or hybrid (combined)"
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 10,
                "description": "Number of results to return"
            },
            "min_relevance": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.5,
                "description": "Minimum relevance threshold (0.0 to 1.0)"
            }
        },
        "required": ["query"]
    },
    "tool_output_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Original search query"
            },
            "search_type": {
                "type": "string",
                "description": "Search method used"
            },
            "total_count": {
                "type": "integer",
                "description": "Total number of results returned"
            },
            "execution_time_ms": {
                "type": "integer",
                "description": "Query execution time in milliseconds"
            },
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chunk_id": {"type": "string"},
                        "document_id": {"type": "string"},
                        "document_name": {"type": "string"},
                        "chunk_text": {"type": "string"},
                        "page_number": {"type": ["integer", "null"]},
                        "relevance_score": {"type": "number"},
                        "chunk_type": {"type": "string"}
                    }
                },
                "description": "Search result chunks with relevance scores"
            }
        }
    },
    "tags": {
        "category": "document",
        "version": "1.0",
        "ops_integration": "document_search",
        "search_types": "hybrid,vector,text"
    }
}


def init_document_search_tool(session: Session, api_base_url: str = None):
    """
    Initialize Document Search Tool Asset

    Args:
        session: Database session
        api_base_url: Base URL for API (default: http://localhost:8000)
    """

    if api_base_url is None:
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    # Update URL in config
    config = json.loads(json.dumps(DOCUMENT_SEARCH_TOOL_CONFIG))
    config["tool_config"]["url"] = config["tool_config"]["url"].replace(
        "{API_BASE_URL}", api_base_url
    )

    print(f"Initializing Document Search Tool Asset...")
    print(f"  API Base URL: {api_base_url}")
    print(f"  Tool Type: {config['tool_type']}")
    print(f"  Tool Config URL: {config['tool_config']['url']}")

    try:
        # Check if tool already exists
        from sqlalchemy import select
        stmt = select(TbAssetRegistry).where(
            (TbAssetRegistry.name == "document_search") &
            (TbAssetRegistry.asset_type == "tool")
        )
        existing = session.exec(stmt).first()

        if existing:
            print(f"\n⚠️  Document Search Tool already exists (ID: {existing.asset_id})")
            print(f"   Status: {existing.status}")
            return existing

        # Create tool asset
        tool_asset = create_tool_asset(
            session=session,
            name=config["name"],
            description=config["description"],
            tool_type=config["tool_type"],
            tool_config=config["tool_config"],
            tool_input_schema=config["tool_input_schema"],
            tool_output_schema=config["tool_output_schema"],
            tags=config["tags"],
            created_by="system",
        )

        print(f"\n✅ Tool Asset created: {tool_asset.asset_id}")
        print(f"   Name: {tool_asset.name}")
        print(f"   Status: {tool_asset.status}")

        # Publish tool asset
        published_asset = publish_asset(
            session=session,
            asset=tool_asset,
            published_by="system",
        )

        print(f"\n✅ Tool Asset published")
        print(f"   Version: {published_asset.version}")
        print(f"   Status: {published_asset.status}")
        print(f"   Published At: {published_asset.published_at}")

        # Display usage information
        print(f"\n" + "="*70)
        print(f"DOCUMENT SEARCH TOOL REGISTERED SUCCESSFULLY")
        print(f"="*70)
        print(f"\nTool Asset ID: {published_asset.asset_id}")
        print(f"Tool Name: {published_asset.name}")
        print(f"\nUsage in OPS CI Ask:")
        print(f"  - Tool will automatically be discovered by OPS CI Planner")
        print(f"  - User questions about documents will trigger this tool")
        print(f"  - Search results will be included in LLM context")
        print(f"\nEndpoint Details:")
        print(f"  - URL: {config['tool_config']['url']}")
        print(f"  - Method: {config['tool_config']['method']}")
        print(f"  - Type: {config['tool_type']}")
        print(f"\n" + "="*70)

        return published_asset

    except Exception as e:
        print(f"\n❌ Error creating tool asset: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main entry point"""

    print("\n" + "="*70)
    print("DOCUMENT SEARCH TOOL INITIALIZATION")
    print("="*70)

    try:
        with Session(engine) as session:
            tool_asset = init_document_search_tool(session)
            print("\n✅ Initialization complete!")
            return 0

    except Exception as e:
        print(f"\n❌ Initialization failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

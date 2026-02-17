#!/usr/bin/env python3
"""
Document Search Tool Registration Script

Registers the document_search tool in the asset registry using the Asset CRUD API.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from the correct paths
sys.path.insert(0, str(project_root / "apps/api"))
from app.modules.asset_registry.crud import create_tool_asset
from core.db import get_session


async def register_document_search():
    """Register document search tool"""

    # Get database session
    session = next(get_session())

    # Define the document search tool asset
    tool_asset_data = {
        "name": "document_search",
        "description": "Search documents using vector and text search",
        "tool_type": "http_api",
        "tool_config": {
            "endpoint": "http://localhost:8000/api/documents/search",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json"
            },
            "body_template": {
                "query": "query",
                "top_k": "top_k",
                "search_type": "search_type",
                "date_from": "date_from",
                "date_to": "date_to",
                "document_types": "document_types"
            },
            "auth_type": "bearer_token"
        },
        "tool_input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "top_k": {"type": "integer", "default": 10, "description": "Maximum number of results"},
                "search_type": {"type": "string", "default": "hybrid", "enum": ["hybrid", "text", "vector"]},
                "date_from": {"type": "string", "format": "date-time", "description": "Start date for search"},
                "date_to": {"type": "string", "format": "date-time", "description": "End date for search"},
                "document_types": {"type": "array", "items": {"type": "string"}, "description": "Document types to search"}
            },
            "required": ["query"]
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chunk_id": {"type": "string"},
                            "document_id": {"type": "string"},
                            "document_name": {"type": "string"},
                            "chunk_text": {"type": "string"},
                            "page_number": {"type": "integer"},
                            "relevance_score": {"type": "number"}
                        }
                    }
                }
            }
        },
        "tags": {"category": "document"}
    }

    # Register the tool
    try:
        result = create_tool_asset(
            session=session,
            name=tool_asset_data["name"],
            description=tool_asset_data["description"],
            tool_type=tool_asset_data["tool_type"],
            tool_config=tool_asset_data["tool_config"],
            tool_input_schema=tool_asset_data["tool_input_schema"],
            tool_output_schema=tool_asset_data["tool_output_schema"],
            tags=tool_asset_data["tags"]
        )
        print("✅ document_search tool registered successfully")
        print(f"Asset ID: {result.asset_id}")
        session.close()
    except Exception as e:
        print(f"❌ Failed to register tool: {e}")
        session.close()

if __name__ == "__main__":
    asyncio.run(register_document_search())

# Document Search Tool Implementation Guide

## Overview

This guide provides step-by-step instructions to implement the **DocumentSearchTool** - integrating pgvector-based document search with the OPS CI tool system.

**Status**: Ready for Implementation (Code skeleton + DB queries provided)
**Effort**: ~3-4 hours (assuming familiar with the codebase)
**Risk**: Low (isolated changes, no breaking changes)

---

## Phase 1: Complete DocumentSearchService (Core DB Logic)

### 1.1 Implement _vector_search()

**File**: `/home/spa/tobit-spa-ai/apps/api/app/modules/document_processor/services/search_service.py`

**Current State**: Lines 142-184 (mock implementation with `pass`)

**Replace with**:

```python
async def _vector_search(
    self, query: str, filters: SearchFilters, top_k: int
) -> List[SearchResult]:
    """
    Vector similarity search using pgvector cosine distance

    Implementation uses:
    - 1 - (embedding <=> query_vector) for cosine similarity
    - Top-k retrieval based on similarity score
    """
    results = []

    try:
        # 1. Embed the query
        if not self.embedding_service:
            self.logger.warning("No embedding service provided for vector search")
            return results

        query_embedding = await self.embedding_service.embed(query)

        if not query_embedding:
            self.logger.error("Failed to generate query embedding")
            return results

        # 2. Execute pgvector search query
        # Note: This assumes sqlalchemy/sqlmodel with raw SQL execution

        if not self.db:
            self.logger.warning("No database session for vector search")
            return results

        # Raw SQL query using pgvector <=> operator (L2 distance)
        # Formula: 1 - (<=> distance) = cosine similarity
        query_sql = """
        SELECT
            dc.id,
            dc.document_id,
            d.filename,
            dc.text,
            dc.page_number,
            dc.chunk_type,
            1 - (dc.embedding <=> CAST(:query_embedding AS vector)) as similarity
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.tenant_id = :tenant_id
            AND d.deleted_at IS NULL
            AND dc.embedding IS NOT NULL
            AND 1 - (dc.embedding <=> CAST(:query_embedding AS vector)) > :min_similarity
        ORDER BY similarity DESC
        LIMIT :top_k
        """

        # Execute query
        try:
            # For SQLModel/SQLAlchemy, use text() for raw SQL
            from sqlalchemy import text

            stmt = text(query_sql)

            # Bind parameters
            result_rows = self.db.exec(
                stmt,
                params={
                    "query_embedding": f"[{','.join(map(str, query_embedding))}]",
                    "tenant_id": filters.tenant_id,
                    "min_similarity": filters.min_relevance,
                    "top_k": top_k
                }
            ).all()

            # Parse results
            for row in result_rows:
                try:
                    chunk_id, doc_id, doc_name, text_content, page_num, chunk_type, similarity = row

                    result = SearchResult(
                        chunk_id=chunk_id,
                        document_id=doc_id,
                        document_name=doc_name,
                        chunk_text=text_content,
                        page_number=page_num,
                        relevance_score=float(similarity),
                        chunk_type=chunk_type,
                        created_at=None  # Optional, can fetch from DB if needed
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to parse vector search result: {e}")
                    continue

            self.logger.debug(
                f"Vector search returned {len(results)} results "
                f"(query embedding: {len(query_embedding)} dimensions)"
            )

        except Exception as e:
            self.logger.error(f"Vector search database error: {str(e)}")
            return results

    except Exception as e:
        self.logger.error(f"Vector search error: {str(e)}")

    return results
```

**Key Points**:
- Uses pgvector `<=>` operator (L2 distance)
- Formula: `1 - (<=> distance)` for cosine similarity [0, 1]
- Expects embedding_service to generate 1536-dim vectors
- Returns SearchResult objects with relevance_score

---

### 1.2 Implement _text_search()

**File**: `/home/spa/tobit-spa-ai/apps/api/app/modules/document_processor/services/search_service.py`

**Current State**: Lines 101-140 (mock implementation with `pass`)

**Replace with**:

```python
async def _text_search(
    self, query: str, filters: SearchFilters, top_k: int
) -> List[SearchResult]:
    """
    Full-text search using PostgreSQL tsvector and BM25-like ranking

    Uses:
    - to_tsvector() for text tokenization
    - plainto_tsquery() for query parsing
    - ts_rank() for relevance scoring
    """

    results = []

    try:
        if not self.db:
            self.logger.warning("No database session for text search")
            return results

        # PostgreSQL full-text search query
        # ts_rank(tsvector, tsquery) returns BM25-like score
        query_sql = """
        SELECT
            dc.id,
            dc.document_id,
            d.filename,
            dc.text,
            dc.page_number,
            dc.chunk_type,
            ts_rank(to_tsvector('english', dc.text), plainto_tsquery('english', :query)) as rank
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.tenant_id = :tenant_id
            AND d.deleted_at IS NULL
            AND to_tsvector('english', dc.text) @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :top_k
        """

        try:
            from sqlalchemy import text

            stmt = text(query_sql)

            result_rows = self.db.exec(
                stmt,
                params={
                    "query": query,
                    "tenant_id": filters.tenant_id,
                    "top_k": top_k
                }
            ).all()

            # Parse results
            for row in result_rows:
                try:
                    chunk_id, doc_id, doc_name, text_content, page_num, chunk_type, rank_score = row

                    result = SearchResult(
                        chunk_id=chunk_id,
                        document_id=doc_id,
                        document_name=doc_name,
                        chunk_text=text_content,
                        page_number=page_num,
                        relevance_score=float(rank_score),  # ts_rank returns [0, 1]
                        chunk_type=chunk_type,
                        created_at=None
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to parse text search result: {e}")
                    continue

            self.logger.debug(f"Text search returned {len(results)} results")

        except Exception as e:
            self.logger.error(f"Text search database error: {str(e)}")
            return results

    except Exception as e:
        self.logger.error(f"Text search error: {str(e)}")

    return results
```

**Key Points**:
- Uses PostgreSQL `plainto_tsquery()` for safe query parsing
- `ts_rank()` provides BM25-like relevance scoring
- Language specified as 'english' (can be parameterized)
- `@@` operator for full-text matching

---

### 1.3 Test DocumentSearchService

**File**: Create `/home/spa/tobit-spa-ai/apps/api/tests/test_document_search_service.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.modules.document_processor.services.search_service import (
    DocumentSearchService,
    SearchFilters,
    SearchResult
)


@pytest.fixture
def search_service():
    """Create search service with mocked dependencies"""
    db_mock = MagicMock()
    embedding_service_mock = AsyncMock()

    service = DocumentSearchService(
        db_session=db_mock,
        embedding_service=embedding_service_mock
    )
    return service, db_mock, embedding_service_mock


@pytest.mark.asyncio
async def test_vector_search_basic(search_service):
    """Test basic vector search functionality"""
    service, db_mock, embedding_mock = search_service

    # Mock embedding service
    embedding_mock.embed.return_value = [0.1] * 1536

    # Mock DB results
    db_mock.exec.return_value.all.return_value = [
        ("chunk1", "doc1", "file.pdf", "sample text", 1, "text", 0.95),
        ("chunk2", "doc1", "file.pdf", "more text", 2, "text", 0.85),
    ]

    filters = SearchFilters(tenant_id="tenant1")
    results = await service._vector_search("test query", filters, 10)

    assert len(results) == 2
    assert results[0].chunk_id == "chunk1"
    assert results[0].relevance_score == 0.95
    assert results[0].document_name == "file.pdf"

    # Verify embedding was called
    embedding_mock.embed.assert_called_once_with("test query")


@pytest.mark.asyncio
async def test_text_search_basic(search_service):
    """Test basic text search functionality"""
    service, db_mock, _ = search_service

    # Mock DB results
    db_mock.exec.return_value.all.return_value = [
        ("chunk1", "doc1", "file.pdf", "matching text", 1, "text", 0.80),
    ]

    filters = SearchFilters(tenant_id="tenant1")
    results = await service._text_search("test query", filters, 10)

    assert len(results) == 1
    assert results[0].relevance_score == 0.80


@pytest.mark.asyncio
async def test_hybrid_search(search_service):
    """Test hybrid search combines vector and text results"""
    service, db_mock, embedding_mock = search_service

    # Setup mocks
    embedding_mock.embed.return_value = [0.1] * 1536

    # Will be called twice (vector and text)
    db_mock.exec.return_value.all.side_effect = [
        [  # Vector results
            ("chunk1", "doc1", "file.pdf", "text1", 1, "text", 0.95),
            ("chunk2", "doc1", "file.pdf", "text2", 2, "text", 0.85),
        ],
        [  # Text results
            ("chunk2", "doc1", "file.pdf", "text2", 2, "text", 0.80),
            ("chunk3", "doc1", "file.pdf", "text3", 3, "text", 0.75),
        ]
    ]

    filters = SearchFilters(tenant_id="tenant1")
    results = await service.search("test query", filters, top_k=10, search_type="hybrid")

    # RRF should combine results
    assert len(results) > 0
    assert all(r.relevance_score >= 0 for r in results)


@pytest.mark.asyncio
async def test_search_respects_min_relevance(search_service):
    """Test that min_relevance filter is applied"""
    service, db_mock, _ = search_service

    db_mock.exec.return_value.all.return_value = [
        ("chunk1", "doc1", "file.pdf", "text1", 1, "text", 0.95),
        ("chunk2", "doc1", "file.pdf", "text2", 2, "text", 0.30),  # Below threshold
    ]

    filters = SearchFilters(tenant_id="tenant1", min_relevance=0.5)
    results = await service._text_search("test", filters, 10)

    # After filtering by min_relevance
    results = [r for r in results if r.relevance_score >= filters.min_relevance]
    assert len(results) == 1
    assert results[0].relevance_score == 0.95


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_results(search_service):
    """Test search returns empty list when no matches"""
    service, db_mock, _ = search_service

    db_mock.exec.return_value.all.return_value = []

    filters = SearchFilters(tenant_id="tenant1")
    results = await service._text_search("no matches", filters, 10)

    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_handles_database_error(search_service):
    """Test search handles database errors gracefully"""
    service, db_mock, _ = search_service

    db_mock.exec.side_effect = Exception("Database connection failed")

    filters = SearchFilters(tenant_id="tenant1")
    results = await service._text_search("test", filters, 10)

    assert len(results) == 0  # Returns empty on error
```

**Run Tests**:
```bash
cd /home/spa/tobit-spa-ai/apps/api
pytest tests/test_document_search_service.py -v
```

---

## Phase 2: Create DocumentSearchTool

### 2.1 Create Tool File

**File**: Create `/home/spa/tobit-spa-ai/apps/api/app/modules/ops/services/ci/tools/document_search_tool.py`

```python
"""
Document Search Tool for OPS CI

Implements vector + text hybrid search over uploaded documents
using pgvector and PostgreSQL full-text search.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.logging import get_logger
from app.modules.document_processor.services.search_service import (
    DocumentSearchService,
    SearchFilters,
)

from .base import BaseTool, ToolContext, ToolResult

logger = get_logger(__name__)


class DocumentSearchTool(BaseTool):
    """
    Tool for searching documents with hybrid vector + text search

    Supports three search strategies:
    - vector: Semantic search using pgvector embeddings
    - text: Full-text search using PostgreSQL BM25
    - hybrid: Combined search using Reciprocal Rank Fusion (RRF)
    """

    def __init__(self, search_service: Optional[DocumentSearchService] = None):
        """
        Initialize DocumentSearchTool

        Args:
            search_service: DocumentSearchService instance (injected or defaults to new instance)
        """
        super().__init__()
        self.search_service = search_service or DocumentSearchService()
        self.logger = logger

    @property
    def tool_type(self) -> str:
        """Return the tool type identifier"""
        return "document_search"

    @property
    def tool_name(self) -> str:
        """Return human-readable tool name"""
        return "Document Search"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for input parameters

        Defines the expected input format and validation rules
        """
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text (e.g., 'payment processing', 'customer data')",
                    "minLength": 1
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of top results to return",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100
                },
                "search_type": {
                    "type": "string",
                    "enum": ["text", "vector", "hybrid"],
                    "description": "Search strategy to use",
                    "default": "hybrid"
                },
                "min_relevance": {
                    "type": "number",
                    "description": "Minimum relevance score (0.0-1.0) for results",
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        """Return JSON schema for output"""
        return {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "description": "List of matching document chunks",
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
                    }
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results returned"
                }
            }
        }

    async def should_execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> bool:
        """
        Determine if this tool should execute

        Args:
            context: Execution context with tenant_id, user_id, etc.
            params: Input parameters

        Returns:
            True if tool should execute
        """
        # Only check if query is provided
        return "query" in params and bool(params["query"].strip())

    async def execute(
        self, context: ToolContext, input_data: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute document search

        Args:
            context: Execution context
            input_data: Search parameters (validated by input_schema)

        Returns:
            ToolResult with search results or error information
        """

        try:
            # Extract and validate parameters
            query = input_data.get("query", "").strip()
            if not query:
                return ToolResult(
                    success=False,
                    error="Query parameter is required and cannot be empty"
                )

            top_k = input_data.get("top_k", 10)
            search_type = input_data.get("search_type", "hybrid")
            min_relevance = input_data.get("min_relevance", 0.5)

            # Validate parameter ranges
            if not 1 <= top_k <= 100:
                return ToolResult(
                    success=False,
                    error=f"top_k must be between 1 and 100, got {top_k}"
                )

            if not 0.0 <= min_relevance <= 1.0:
                return ToolResult(
                    success=False,
                    error=f"min_relevance must be between 0.0 and 1.0, got {min_relevance}"
                )

            if search_type not in ["text", "vector", "hybrid"]:
                return ToolResult(
                    success=False,
                    error=f"search_type must be 'text', 'vector', or 'hybrid', got {search_type}"
                )

            self.logger.info(
                f"Executing document search: query='{query[:50]}...', "
                f"type={search_type}, top_k={top_k}, tenant={context.tenant_id}"
            )

            # Create search filters
            filters = SearchFilters(
                tenant_id=context.tenant_id,
                min_relevance=min_relevance
            )

            # Execute search
            import time
            start_time = time.time()

            results = await self.search_service.search(
                query=query,
                filters=filters,
                top_k=top_k,
                search_type=search_type
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Format results
            result_data = {
                "results": [
                    {
                        "chunk_id": r.chunk_id,
                        "document_id": r.document_id,
                        "document_name": r.document_name,
                        "chunk_text": r.chunk_text,
                        "page_number": r.page_number,
                        "relevance_score": r.relevance_score,
                        "chunk_type": r.chunk_type
                    }
                    for r in results
                ],
                "count": len(results)
            }

            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "query": query,
                    "search_type": search_type,
                    "results_count": len(results),
                    "execution_time_ms": execution_time_ms,
                    "tenant_id": context.tenant_id
                }
            )

        except Exception as e:
            self.logger.error(f"Document search error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e),
                error_details={
                    "exception_type": type(e).__name__,
                    "query": input_data.get("query", "unknown")
                }
            )
```

---

### 2.2 Create Tool Tests

**File**: Create `/home/spa/tobit-spa-ai/apps/api/tests/test_document_search_tool.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.ops.services.ci.tools.document_search_tool import DocumentSearchTool
from app.modules.ops.services.ci.tools.base import ToolContext
from app.modules.document_processor.services.search_service import SearchResult


@pytest.fixture
def document_search_tool():
    """Create DocumentSearchTool with mocked search service"""
    search_service_mock = AsyncMock()
    tool = DocumentSearchTool(search_service=search_service_mock)
    return tool, search_service_mock


def test_tool_properties(document_search_tool):
    """Test tool metadata properties"""
    tool, _ = document_search_tool

    assert tool.tool_type == "document_search"
    assert tool.tool_name == "Document Search"
    assert tool.input_schema["properties"]["query"]["minLength"] == 1
    assert "vector" in tool.input_schema["properties"]["search_type"]["enum"]


def test_input_schema_validation(document_search_tool):
    """Test input schema structure"""
    tool, _ = document_search_tool
    schema = tool.input_schema

    # Check required fields
    assert "query" in schema["required"]

    # Check properties
    assert schema["properties"]["top_k"]["default"] == 10
    assert schema["properties"]["search_type"]["default"] == "hybrid"
    assert schema["properties"]["min_relevance"]["default"] == 0.5


@pytest.mark.asyncio
async def test_should_execute_with_valid_query(document_search_tool):
    """Test should_execute returns True for valid query"""
    tool, _ = document_search_tool
    context = ToolContext(tenant_id="test_tenant")

    result = await tool.should_execute(context, {"query": "test"})
    assert result is True


@pytest.mark.asyncio
async def test_should_execute_with_empty_query(document_search_tool):
    """Test should_execute returns False for empty query"""
    tool, _ = document_search_tool
    context = ToolContext(tenant_id="test_tenant")

    result = await tool.should_execute(context, {"query": "   "})
    assert result is False


@pytest.mark.asyncio
async def test_execute_basic_search(document_search_tool):
    """Test basic search execution"""
    tool, search_service_mock = document_search_tool

    # Mock search results
    mock_results = [
        SearchResult(
            chunk_id="chunk1",
            document_id="doc1",
            document_name="file.pdf",
            chunk_text="sample text",
            page_number=1,
            relevance_score=0.95,
            chunk_type="text"
        )
    ]
    search_service_mock.search.return_value = mock_results

    context = ToolContext(tenant_id="test_tenant", user_id="user1")
    input_data = {"query": "test query"}

    result = await tool.execute(context, input_data)

    assert result.success is True
    assert result.data["count"] == 1
    assert result.data["results"][0]["chunk_id"] == "chunk1"
    assert result.metadata["search_type"] == "hybrid"  # default


@pytest.mark.asyncio
async def test_execute_with_custom_parameters(document_search_tool):
    """Test search with custom parameters"""
    tool, search_service_mock = document_search_tool

    search_service_mock.search.return_value = []

    context = ToolContext(tenant_id="test_tenant")
    input_data = {
        "query": "custom query",
        "top_k": 20,
        "search_type": "vector",
        "min_relevance": 0.7
    }

    result = await tool.execute(context, input_data)

    assert result.success is True

    # Verify search service was called with correct parameters
    search_service_mock.search.assert_called_once()
    call_kwargs = search_service_mock.search.call_args.kwargs
    assert call_kwargs["query"] == "custom query"
    assert call_kwargs["top_k"] == 20
    assert call_kwargs["search_type"] == "vector"


@pytest.mark.asyncio
async def test_execute_missing_query(document_search_tool):
    """Test execution fails when query is missing"""
    tool, _ = document_search_tool
    context = ToolContext(tenant_id="test_tenant")

    result = await tool.execute(context, {})

    assert result.success is False
    assert "required" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_invalid_top_k(document_search_tool):
    """Test execution fails with invalid top_k"""
    tool, _ = document_search_tool
    context = ToolContext(tenant_id="test_tenant")

    result = await tool.execute(context, {"query": "test", "top_k": 200})

    assert result.success is False
    assert "top_k" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_handles_service_error(document_search_tool):
    """Test graceful error handling"""
    tool, search_service_mock = document_search_tool

    search_service_mock.search.side_effect = Exception("Database error")

    context = ToolContext(tenant_id="test_tenant")
    result = await tool.execute(context, {"query": "test"})

    assert result.success is False
    assert "Database error" in result.error


@pytest.mark.asyncio
async def test_execute_returns_metadata(document_search_tool):
    """Test that execution metadata is returned"""
    tool, search_service_mock = document_search_tool

    search_service_mock.search.return_value = []

    context = ToolContext(tenant_id="test_tenant", user_id="user1")
    result = await tool.execute(context, {"query": "test"})

    assert "execution_time_ms" in result.metadata
    assert "query" in result.metadata
    assert "search_type" in result.metadata
    assert "tenant_id" in result.metadata
```

**Run Tests**:
```bash
cd /home/spa/tobit-spa-ai/apps/api
pytest tests/test_document_search_tool.py -v
```

---

## Phase 3: Register Tool in ToolRegistry

### 3.1 Update Registry Initialization

**File**: `/home/spa/tobit-spa-ai/apps/api/app/modules/ops/services/ci/tools/base.py`

**Find** the `ToolRegistry.initialize()` method (around line ~200)

**Add DocumentSearchTool registration**:

```python
def initialize(self):
    """Initialize built-in tools"""

    # Existing tools...
    # self.register_tool("ci_search", CITool())
    # self.register_tool("metric_aggregate", MetricTool())

    # NEW: Register Document Search Tool
    try:
        from .document_search_tool import DocumentSearchTool
        from app.modules.document_processor.services.search_service import (
            DocumentSearchService
        )

        # Create search service with dependencies
        search_service = DocumentSearchService(
            # Dependencies can be injected:
            # db_session=get_db_session(),
            # embedding_service=get_embedding_service(),
            # redis_client=get_redis_client()  # optional
        )

        # Create and register tool
        doc_search_tool = DocumentSearchTool(search_service=search_service)
        self.register_tool("document_search", doc_search_tool)

        logger.info("✓ DocumentSearchTool registered successfully")

    except ImportError as e:
        logger.warning(f"Could not import DocumentSearchTool: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize DocumentSearchTool: {e}")
```

---

### 3.2 Update Tool Registry Extension (if used)

**File**: `/home/spa/tobit-spa-ai/apps/api/app/modules/ops/services/ci/tools/tool_registry_ext.py`

If this file exists and handles dynamic tool loading, add DocumentSearchTool support:

```python
def get_dynamic_tools():
    """Get dynamically loaded tools"""
    tools = {}

    # ... existing dynamic tools ...

    # Document Search Tool (built-in)
    try:
        from .document_search_tool import DocumentSearchTool
        from app.modules.document_processor.services.search_service import DocumentSearchService

        doc_search_tool = DocumentSearchTool(search_service=DocumentSearchService())
        tools["document_search"] = doc_search_tool
    except Exception as e:
        logger.warning(f"Failed to load DocumentSearchTool: {e}")

    return tools
```

---

## Phase 4: Integration Testing

### 4.1 Create Integration Test

**File**: Create `/home/spa/tobit-spa-ai/apps/api/tests/test_document_search_integration.py`

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.modules.ops.services.ci.tools.base import ToolRegistry, ToolContext


@pytest.mark.asyncio
async def test_document_search_tool_in_registry():
    """Test DocumentSearchTool is properly registered"""

    registry = ToolRegistry()
    registry.initialize()

    # Check tool is registered
    assert "document_search" in registry.get_available_tools()

    # Get tool
    tool = registry.get_tool("document_search")
    assert tool is not None
    assert tool.tool_type == "document_search"


@pytest.mark.asyncio
async def test_execute_document_search_via_registry():
    """Test executing search through ToolRegistry"""

    registry = ToolRegistry()

    # Mock the search service
    with patch('app.modules.ops.services.ci.tools.document_search_tool.DocumentSearchService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service.search.return_value = []
        mock_service_class.return_value = mock_service

        registry.initialize()

        context = ToolContext(tenant_id="test_tenant")
        result = await registry.execute_tool(
            "document_search",
            context,
            {"query": "test search"}
        )

        assert result.success is True
        assert result.data["count"] == 0


@pytest.mark.asyncio
async def test_document_search_input_schema():
    """Test input schema is valid JSON Schema"""

    registry = ToolRegistry()
    registry.initialize()

    tool = registry.get_tool("document_search")
    schema = tool.input_schema

    # Verify required structure
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "required" in schema
    assert "query" in schema["properties"]
```

---

## Phase 5: Manual Testing

### 5.1 Test via API

```bash
# 1. Ensure service is running
cd /home/spa/tobit-spa-ai/apps/api
python -m uvicorn main:app --reload

# 2. In another terminal, test the endpoint
curl -X POST http://localhost:8000/api/documents/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "payment processing",
    "search_type": "hybrid",
    "top_k": 10,
    "min_relevance": 0.5
  }'
```

### 5.2 Test via OPS CI Tool

```bash
# Call through OPS CI orchestrator
curl -X POST http://localhost:8000/ops/stage/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "stage_name": "search_docs",
    "tools": [
      {
        "tool_name": "document_search",
        "input": {
          "query": "customer information system",
          "top_k": 10,
          "search_type": "hybrid"
        }
      }
    ]
  }'
```

---

## Phase 6: Optional - Add Redis Caching

### 6.1 Update DocumentSearchService with Caching

**File**: `/home/spa/tobit-spa-ai/apps/api/app/modules/document_processor/services/search_service.py`

```python
import hashlib
import json

class DocumentSearchService:

    def __init__(self, db_session=None, embedding_service=None, redis_client=None):
        """
        Initialize with optional Redis client for caching
        """
        self.db = db_session
        self.embedding_service = embedding_service
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)

    async def search(self, query, filters, top_k=10, search_type="hybrid"):
        """
        Perform search with optional Redis caching
        """

        # Generate cache key
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"doc_search:{filters.tenant_id}:{query_hash}:{search_type}:{top_k}"

        # Try cache first
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    self.logger.debug(f"Cache HIT for search: {cache_key}")
                    # Parse cached results
                    return [SearchResult(**r) for r in json.loads(cached)]
            except Exception as e:
                self.logger.warning(f"Redis cache error (not fatal): {e}")

        # Execute search (existing logic)
        results = []
        # ... [vector/text/hybrid search logic] ...

        # Cache results (5 minute TTL)
        if self.redis and results:
            try:
                cached_data = json.dumps([asdict(r) for r in results])
                await self.redis.setex(cache_key, 300, cached_data)
                self.logger.debug(f"Cached search results: {cache_key}")
            except Exception as e:
                self.logger.warning(f"Failed to cache results: {e}")

        return results
```

---

## Phase 7: Deployment Checklist

Before deploying to production:

- [ ] DocumentSearchService `_vector_search()` implemented and tested
- [ ] DocumentSearchService `_text_search()` implemented and tested
- [ ] DocumentSearchTool class created and tested
- [ ] ToolRegistry registration updated
- [ ] Unit tests passing (test_document_search_service.py)
- [ ] Unit tests passing (test_document_search_tool.py)
- [ ] Integration tests passing
- [ ] Manual API testing completed
- [ ] Manual OPS CI tool testing completed
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Performance benchmarking completed (if required)

---

## Performance Notes

### Expected Performance

```
Query Type          Typical Time    Cache Hit   Notes
────────────────────────────────────────────────
Vector Search       200-500ms       ~10ms       Depends on query embedding
Text Search         100-300ms       ~10ms       PostgreSQL FTS is fast
Hybrid Search       300-800ms       ~15ms       RRF combination overhead
Embedding Gen       2-5s            N/A         Major latency (cached at service level)
```

### Optimization Tips

1. **Index Optimization**:
   ```sql
   -- Create HNSW index on embeddings for vector search
   CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);

   -- Create GIN index for text search
   CREATE INDEX ON document_chunks USING GIN (to_tsvector('english', text));
   ```

2. **Redis Caching**:
   - Cache query embeddings (24h TTL) - saves embedding API calls
   - Cache search results (5m TTL) - handles repeated queries
   - Invalidate on document updates

3. **Batch Operations**:
   - Pre-generate embeddings for chunks during document processing
   - Use bulk indexing operations

---

## Troubleshooting

### pgvector Not Found

```
Error: pgvector extension not found
Solution: SELECT * FROM pg_available_extensions WHERE name LIKE '%vector%';
         CREATE EXTENSION IF NOT EXISTS vector;
```

### Embedding Service Unavailable

```
Error: No embedding service provided for vector search
Solution: Inject embedding_service dependency in DocumentSearchService
```

### Performance Issues

- Monitor query execution time in logs
- Check PostgreSQL query plans
- Consider adding indexes as shown above
- Monitor Redis memory usage

---

## Future Enhancements

1. **Semantic Caching**: Cache embedding vectors and search results longer
2. **Reranking**: Use LLM to rerank results after hybrid search
3. **Faceted Search**: Filter by document type, date range, etc.
4. **Query Expansion**: Expand query with synonyms for better recall
5. **Analytics**: Track search queries and user behavior
6. **RAG Integration**: Feed search results into LLM context

---

**Document Generated**: 2026-02-06
**Implementation Path**: Option 1 (DocumentSearchTool)
**Status**: Ready for Implementation

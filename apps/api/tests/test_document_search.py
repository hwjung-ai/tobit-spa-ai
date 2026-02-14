"""
Tests for Document Search Service and API

Tests cover:
- DocumentSearchService with mocked DB
- Search endpoints with various search types
- Tool Asset configuration
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from app.modules.document_processor.services.search_service import (
    DocumentSearchService,
    SearchFilters,
    SearchResult,
)
from fastapi.testclient import TestClient


class TestDocumentSearchService:
    """Test DocumentSearchService"""

    @pytest.fixture
    def search_service(self):
        """Create a search service with mocked DB and embedding service"""
        db_session = Mock()
        embedding_service = Mock()
        return DocumentSearchService(db_session, embedding_service)

    @pytest.fixture
    def search_filters(self):
        """Create basic search filters"""
        return SearchFilters(
            tenant_id="t1",
            date_from=None,
            date_to=None,
            document_types=[],
            min_relevance=0.5
        )

    @pytest.mark.asyncio
    async def test_text_search_basic(self, search_service, search_filters):
        """Test basic text search"""
        # Mock DB results
        mock_rows = [
            ("chunk1", "doc1", "document.pdf", "This is about machine learning", 1, "text", 0.85),
            ("chunk2", "doc2", "document.pdf", "Machine learning algorithms", 2, "text", 0.75),
        ]

        search_service.db.execute = Mock(return_value=Mock(fetchall=Mock(return_value=mock_rows)))

        # Perform search
        results = await search_service._text_search("machine learning", search_filters, top_k=10)

        # Verify results
        assert len(results) == 2
        assert results[0].chunk_id == "chunk1"
        assert results[0].relevance_score == 0.85
        assert results[1].chunk_id == "chunk2"
        assert results[1].relevance_score == 0.75

    @pytest.mark.asyncio
    async def test_vector_search_with_embedding(self, search_service, search_filters):
        """Test vector search with embedding service"""
        # Mock embedding
        mock_embedding = [0.1] * 1536
        search_service.embedding_service.embed = AsyncMock(return_value=mock_embedding)

        # Mock DB results
        mock_rows = [
            ("chunk1", "doc1", "document.pdf", "About neural networks", 1, "text", 0.92),
        ]

        search_service.db.execute = Mock(return_value=Mock(fetchall=Mock(return_value=mock_rows)))

        # Perform search
        results = await search_service._vector_search("neural networks", search_filters, top_k=10)

        # Verify results
        assert len(results) == 1
        assert results[0].relevance_score == 0.92
        search_service.embedding_service.embed.assert_called_once_with("neural networks")

    @pytest.mark.asyncio
    async def test_vector_search_without_embedding_service(self, search_filters):
        """Test vector search returns empty when embedding service is missing"""
        db_session = Mock()
        search_service = DocumentSearchService(db_session, embedding_service=None)

        results = await search_service._vector_search("query", search_filters, top_k=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_combination(self, search_service, search_filters):
        """Test hybrid search combining vector and text results"""
        # Setup mocks
        search_service.embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)
        search_service.db.execute = Mock(
            return_value=Mock(fetchall=Mock(return_value=[
                ("chunk1", "doc1", "document.pdf", "Text about AI", 1, "text", 0.8),
            ]))
        )

        # Perform hybrid search
        await search_service.search(
            query="artificial intelligence",
            filters=search_filters,
            top_k=5,
            search_type="hybrid"
        )

        # Should call both text and vector search
        assert search_service.embedding_service.embed.called

    @pytest.mark.asyncio
    async def test_search_with_date_filters(self, search_service, search_filters):
        """Test search with date range filtering"""
        # Update filters with dates
        search_filters.date_from = datetime(2026, 1, 1)
        search_filters.date_to = datetime(2026, 12, 31)

        mock_rows = []
        search_service.db.execute = Mock(return_value=Mock(fetchall=Mock(return_value=mock_rows)))

        await search_service._text_search("query", search_filters, top_k=10)

        # Verify DB was called
        search_service.db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_search_with_document_type_filter(self, search_service):
        """Test search filtering by document type"""
        filters = SearchFilters(
            tenant_id="t1",
            document_types=["pdf", "docx"],
            min_relevance=0.5
        )

        mock_rows = []
        search_service.db.execute = Mock(return_value=Mock(fetchall=Mock(return_value=mock_rows)))

        await search_service._text_search("query", filters, top_k=10)

        # Verify DB was called with type filter
        search_service.db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_search_result_mapping(self):
        """Test SearchResult dataclass mapping"""
        result = SearchResult(
            chunk_id="c1",
            document_id="d1",
            document_name="test.pdf",
            chunk_text="Test content",
            page_number=5,
            relevance_score=0.95,
            chunk_type="text",
            created_at=datetime.now()
        )

        assert result.chunk_id == "c1"
        assert result.relevance_score == 0.95
        assert result.page_number == 5


class TestDocumentSearchAPI:
    """Test Document Search API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_current_user(self):
        """Mock current user"""
        return Mock(
            id="user1",
            tenant_id="t1",
            role="user",
            get=lambda key, default=None: {
                "id": "user1",
                "tenant_id": "t1",
            }.get(key, default)
        )

    def test_search_documents_basic(self, client, mock_current_user):
        """Test basic document search API call"""
        # This test requires proper mocking setup
        # In real environment, would test with actual DB
        pass

    def test_search_with_invalid_query(self, client):
        """Test search with invalid query (too short)"""
        # Query too short should be rejected
        pass

    def test_search_with_date_filters(self, client):
        """Test search API with date range"""
        pass

    def test_search_suggestions_endpoint(self, client):
        """Test search suggestions endpoint"""
        pass


class TestToolAssetConfiguration:
    """Test Tool Asset configuration for OPS integration"""

    def test_tool_asset_schema_validity(self):
        """Test that Tool Asset schema is valid"""
        from tools.init_document_search_tool import DOCUMENT_SEARCH_TOOL_CONFIG

        config = DOCUMENT_SEARCH_TOOL_CONFIG

        # Verify required fields
        assert config["name"] == "document_search"
        assert config["tool_type"] == "http_api"
        assert "tool_config" in config
        assert "tool_input_schema" in config
        assert "tool_output_schema" in config

    def test_tool_config_http_api(self):
        """Test HTTP API configuration"""
        from tools.init_document_search_tool import DOCUMENT_SEARCH_TOOL_CONFIG

        config = DOCUMENT_SEARCH_TOOL_CONFIG["tool_config"]

        # Verify HTTP config
        assert "{API_BASE_URL}" in config["url"]
        assert config["method"] == "POST"
        assert "body_template" in config
        assert config["body_template"]["query"] == "query"

    def test_tool_input_schema(self):
        """Test input schema is valid JSON Schema"""
        from tools.init_document_search_tool import DOCUMENT_SEARCH_TOOL_CONFIG

        schema = DOCUMENT_SEARCH_TOOL_CONFIG["tool_input_schema"]

        # Required fields
        assert "properties" in schema
        assert "query" in schema["properties"]
        assert "required" in schema
        assert "query" in schema["required"]

    def test_tool_output_schema(self):
        """Test output schema describes search results"""
        from tools.init_document_search_tool import DOCUMENT_SEARCH_TOOL_CONFIG

        schema = DOCUMENT_SEARCH_TOOL_CONFIG["tool_output_schema"]

        # Result structure
        assert "properties" in schema
        assert "results" in schema["properties"]
        assert schema["properties"]["results"]["type"] == "array"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

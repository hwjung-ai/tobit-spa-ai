"""Advanced document search service with hybrid vector + BM25 search"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Search filter criteria"""

    tenant_id: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    document_types: List[str] = field(default_factory=list)
    min_relevance: float = 0.5


@dataclass
class SearchResult:
    """Single search result"""

    chunk_id: str
    document_id: str
    document_name: str
    chunk_text: str
    page_number: Optional[int] = None
    relevance_score: float = 0.0
    chunk_type: str = "text"
    created_at: Optional[datetime] = None


class DocumentSearchService:
    """Advanced document search with hybrid vector + BM25 approach"""

    def __init__(self, db_session=None, embedding_service=None):
        """
        Initialize search service

        Args:
            db_session: Database session
            embedding_service: LLM embedding service for vector search
        """

        self.db = db_session
        self.embedding_service = embedding_service
        self.logger = logging.getLogger(__name__)

    async def search(
        self,
        query: str,
        filters: SearchFilters,
        top_k: int = 10,
        search_type: str = "hybrid",
    ) -> List[SearchResult]:
        """
        Perform hybrid search (vector + BM25 + ranking)

        Args:
            query: Search query text
            filters: Search filter criteria
            top_k: Number of top results to return
            search_type: "vector", "text", or "hybrid"

        Returns:
            List of ranked search results
        """

        start_time = time.time()
        results = []

        try:
            if search_type == "text":
                results = await self._text_search(query, filters, top_k * 2)

            elif search_type == "vector":
                results = await self._vector_search(query, filters, top_k * 2)

            else:  # hybrid (default)
                text_results = await self._text_search(query, filters, top_k * 2)
                vector_results = await self._vector_search(query, filters, top_k * 2)
                results = self._combine_results(text_results, vector_results, top_k * 2)

            # Apply min relevance threshold
            results = [r for r in results if r.relevance_score >= filters.min_relevance]

            # Log search
            execution_time_ms = int((time.time() - start_time) * 1000)
            await self._log_search(query, filters, len(results), execution_time_ms)

            return results[:top_k]

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise

    async def _text_search(
        self, query: str, filters: SearchFilters, top_k: int
    ) -> List[SearchResult]:
        """
        Full-text search using BM25

        In production, this would use PostgreSQL full-text search:
        SELECT chunk_id, document_id, text, ts_rank(...)
        FROM document_chunks
        WHERE to_tsvector(text) @@ plainto_tsquery($1)
        """

        # Placeholder implementation - would be replaced with actual DB query
        results = []

        # Simulate searching through documents
        if self.db:
            try:
                # This would be actual SQL query:
                # query_sql = """
                # SELECT dc.id, dc.document_id, d.filename, dc.text,
                #        dc.page_number, dc.chunk_type,
                #        ts_rank(to_tsvector(dc.text), plainto_tsquery($1)) as rank
                # FROM document_chunks dc
                # JOIN documents d ON d.id = dc.document_id
                # WHERE d.tenant_id = $2
                # AND to_tsvector(dc.text) @@ plainto_tsquery($1)
                # ORDER BY rank DESC
                # LIMIT $3
                # """

                self.logger.debug(f"Performing text search for: {query}")

                # Mock results for now
                pass

            except Exception as e:
                self.logger.error(f"Text search error: {str(e)}")

        return results

    async def _vector_search(
        self, query: str, filters: SearchFilters, top_k: int
    ) -> List[SearchResult]:
        """
        Vector similarity search using pgvector

        Uses cosine similarity on 1536-dimensional embeddings
        """

        results = []

        try:
            # 1. Embed the query
            if not self.embedding_service:
                self.logger.warning("No embedding service provided for vector search")
                return results

            query_embedding = await self.embedding_service.embed(query)

            # 2. Vector search (would be actual pgvector query)
            # query_sql = """
            # SELECT dc.id, dc.document_id, d.filename, dc.text,
            #        dc.page_number, dc.chunk_type,
            #        1 - (dc.embedding <=> $1) as similarity
            # FROM document_chunks dc
            # JOIN documents d ON d.id = dc.document_id
            # WHERE d.tenant_id = $2
            # AND 1 - (dc.embedding <=> $1) > $3
            # ORDER BY similarity DESC
            # LIMIT $4
            # """

            self.logger.debug(
                f"Performing vector search with {len(query_embedding)} dimensions"
            )

            # Mock results for now
            pass

        except Exception as e:
            self.logger.error(f"Vector search error: {str(e)}")

        return results

    @staticmethod
    def _combine_results(
        text_results: List[SearchResult], vector_results: List[SearchResult], top_k: int
    ) -> List[SearchResult]:
        """
        Combine text and vector results using Reciprocal Rank Fusion (RRF)

        RRF formula: score = 1 / (60 + rank)

        This prevents one ranking method from dominating
        """

        scores: Dict[str, float] = {}
        result_map: Dict[str, SearchResult] = {}

        # Score text results
        for rank, result in enumerate(text_results, 1):
            rrf_score = 1 / (60 + rank)
            scores[result.chunk_id] = scores.get(result.chunk_id, 0) + rrf_score
            result_map[result.chunk_id] = result

        # Score vector results
        for rank, result in enumerate(vector_results, 1):
            rrf_score = 1 / (60 + rank)
            scores[result.chunk_id] = scores.get(result.chunk_id, 0) + rrf_score
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[
            :top_k
        ]

        combined = []
        for chunk_id in sorted_ids:
            result = result_map[chunk_id]
            result.relevance_score = scores[chunk_id]
            combined.append(result)

        return combined

    async def _log_search(
        self,
        query: str,
        filters: SearchFilters,
        results_count: int,
        execution_time_ms: int,
    ) -> None:
        """Log search query for analytics"""

        try:
            if self.db:
                # Insert into document_search_log table
                # sql = """
                # INSERT INTO document_search_log
                # (search_id, user_id, tenant_id, query, search_type, results_count, execution_time_ms)
                # VALUES ($1, $2, $3, $4, $5, $6, $7)
                # """

                self.logger.debug(
                    f"Search completed: query={query[:50]}, "
                    f"results={results_count}, time={execution_time_ms}ms"
                )

        except Exception as e:
            self.logger.error(f"Failed to log search: {str(e)}")

    def get_search_suggestions(self, query_prefix: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions based on previous queries

        Args:
            query_prefix: Prefix to match
            limit: Number of suggestions

        Returns:
            List of suggested queries
        """

        # Would query search log for matching queries
        # For now, return empty
        return []

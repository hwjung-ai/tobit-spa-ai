"""Advanced document search service with hybrid vector + BM25 search"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ..search_crud import (
    get_search_suggestions,
    log_search,
    search_chunks_by_text,
    search_chunks_by_vector,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Search filter criteria"""

    tenant_id: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    document_types: List[str] = field(default_factory=list)
    min_relevance: float = 0.01  # BM25 scores are typically 0.01-0.1, not 0.0-1.0


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
                # If vector search fails, fall back to text-only results
                if vector_results:
                    results = self._combine_results(text_results, vector_results, top_k * 2)
                else:
                    results = text_results

            # Apply min relevance threshold (BM25 scores are typically 0.0-0.1, not 0.0-1.0)
            # Use a much lower threshold for BM25 text search results
            min_threshold = 0.01 if search_type in ["text", "hybrid"] else filters.min_relevance
            results = [r for r in results if r.relevance_score >= min_threshold]

            # Log search
            execution_time_ms = int((time.time() - start_time) * 1000)
            await self._log_search(query, filters, len(results), execution_time_ms, search_type)

            return results[:top_k]

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise

    async def _text_search(
        self, query: str, filters: SearchFilters, top_k: int
    ) -> List[SearchResult]:
        """
        Full-text search using BM25 (PostgreSQL tsvector) with ILIKE fallback.

        Uses 'simple' analyzer for multilingual support (Korean, etc.).
        Falls back to ILIKE when tsvector returns no results.
        """

        results = []

        if not self.db:
            return results

        try:
            # Use CRUD for text search
            rows = search_chunks_by_text(
                session=self.db,
                query=query,
                tenant_id=filters.tenant_id,
                top_k=top_k * 2,  # Get more for ranking
                document_types=filters.document_types or None,
                date_from=filters.date_from,
                date_to=filters.date_to,
            )

            # Map results
            for row in rows:
                result = SearchResult(
                    chunk_id=row["id"],
                    document_id=row["document_id"],
                    document_name=row["filename"],
                    chunk_text=row["text"],
                    page_number=row["page_number"],
                    chunk_type=row["chunk_type"],
                    relevance_score=row["score"],
                    created_at=None,
                )
                results.append(result)

            self.logger.debug(f"Text search found {len(results)} results for: {query}")

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

            if not self.db:
                return results

            # Use CRUD for vector search
            rows = search_chunks_by_vector(
                session=self.db,
                query_embedding=query_embedding,
                tenant_id=filters.tenant_id,
                top_k=top_k,
                document_types=filters.document_types or None,
                date_from=filters.date_from,
                date_to=filters.date_to,
            )

            # Map results
            for row in rows:
                result = SearchResult(
                    chunk_id=row["id"],
                    document_id=row["document_id"],
                    document_name=row["filename"],
                    chunk_text=row["text"],
                    page_number=row["page_number"],
                    chunk_type=row["chunk_type"],
                    relevance_score=row["score"],
                    created_at=None,
                )
                results.append(result)

            self.logger.debug(
                f"Vector search found {len(results)} results with {len(query_embedding)} dimensions"
            )

        except Exception as e:
            self.logger.error(f"Vector search error: {str(e)}")
            # Fallback: return empty results, BM25 will be used
            results = []

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
        search_type: str = "hybrid",
    ) -> None:
        """Log search query for analytics and suggestions"""

        try:
            if self.db:
                # Use CRUD for search logging
                log_search(
                    session=self.db,
                    tenant_id=filters.tenant_id,
                    query=query,
                    result_count=results_count,
                    execution_time_ms=execution_time_ms,
                )

            self.logger.info(
                f"Search completed: query={query[:50]}, "
                f"results={results_count}, time={execution_time_ms}ms"
            )

        except Exception as e:
            self.logger.error(f"Failed to log search: {str(e)}")

    def get_search_suggestions(
        self, query_prefix: str, limit: int = 5, tenant_id: str | None = None
    ) -> List[str]:
        """
        Get search suggestions based on previous queries

        Args:
            query_prefix: Prefix to match
            limit: Number of suggestions

        Returns:
            List of suggested queries
        """

        if not self.db or not query_prefix.strip():
            return []

        try:
            # Use CRUD for search suggestions
            return get_search_suggestions(
                session=self.db,
                query_prefix=query_prefix,
                limit=limit,
                tenant_id=tenant_id,
            )
        except Exception as e:
            self.logger.warning(f"Failed to get search suggestions: {str(e)}")
            return []

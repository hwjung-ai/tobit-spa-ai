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
        Full-text search using BM25 (PostgreSQL tsvector) with ILIKE fallback.

        Uses 'simple' analyzer for multilingual support (Korean, etc.).
        Falls back to ILIKE when tsvector returns no results.
        """

        results = []

        if not self.db:
            return results

        try:
            from sqlalchemy import text

            # Common filter clauses
            base_where = ["d.tenant_id = :tenant_id", "d.deleted_at IS NULL"]
            if filters.date_from:
                base_where.append("dc.created_at >= :date_from")
            if filters.date_to:
                base_where.append("dc.created_at <= :date_to")
            if filters.document_types:
                base_where.append("dc.chunk_type = ANY(:doc_types)")

            params = {
                "tenant_id": filters.tenant_id,
                "query": query,
                "top_k": top_k,
            }
            if filters.date_from:
                params["date_from"] = filters.date_from
            if filters.date_to:
                params["date_to"] = filters.date_to
            if filters.document_types:
                params["doc_types"] = filters.document_types

            # 1) Try tsvector with 'simple' analyzer (supports CJK)
            ts_where = base_where + [
                "to_tsvector('simple', dc.text) @@ plainto_tsquery('simple', :query)"
            ]
            query_sql = f"""
            SELECT dc.id, dc.document_id, d.filename, dc.text,
                   dc.page_number, dc.chunk_type,
                   ts_rank(to_tsvector('simple', dc.text),
                           plainto_tsquery('simple', :query)) as score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE {' AND '.join(ts_where)}
            ORDER BY score DESC
            LIMIT :top_k
            """
            rows = self.db.execute(text(query_sql), params).fetchall()

            # 2) Fallback to ILIKE if tsvector returns nothing
            if not rows:
                # Split query into keywords for ILIKE search
                keywords = [kw.strip() for kw in query.split() if len(kw.strip()) >= 2]
                if keywords:
                    ilike_conditions = " OR ".join(
                        [f"dc.text ILIKE :kw{i}" for i in range(len(keywords))]
                    )
                    ilike_where = base_where + [f"({ilike_conditions})"]
                    ilike_sql = f"""
                    SELECT dc.id, dc.document_id, d.filename, dc.text,
                           dc.page_number, dc.chunk_type,
                           0.5 as score
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE {' AND '.join(ilike_where)}
                    LIMIT :top_k
                    """
                    ilike_params = dict(params)
                    for i, kw in enumerate(keywords):
                        ilike_params[f"kw{i}"] = f"%{kw}%"
                    rows = self.db.execute(text(ilike_sql), ilike_params).fetchall()

            # Map results
            for row in rows:
                result = SearchResult(
                    chunk_id=row[0],
                    document_id=row[1],
                    document_name=row[2],
                    chunk_text=row[3],
                    page_number=row[4],
                    chunk_type=row[5],
                    relevance_score=float(row[6]) if row[6] else 0.0,
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

            from sqlalchemy import text
            import json

            # Build WHERE clauses
            where_clauses = [
                "d.tenant_id = :tenant_id",
                "d.deleted_at IS NULL",
                "1 - (dc.embedding <=> :embedding) > :min_similarity",
            ]

            # Add date filters
            if filters.date_from:
                where_clauses.append("dc.created_at >= :date_from")
            if filters.date_to:
                where_clauses.append("dc.created_at <= :date_to")

            # Add document type filter
            if filters.document_types:
                where_clauses.append("dc.chunk_type = ANY(:doc_types)")

            where_clause = " AND ".join(where_clauses)

            # pgvector similarity search query
            query_sql = f"""
            SELECT dc.id, dc.document_id, d.filename, dc.text,
                   dc.page_number, dc.chunk_type,
                   1 - (dc.embedding <=> :embedding::vector) as similarity
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE {where_clause}
            ORDER BY similarity DESC
            LIMIT :top_k
            """

            # Build parameters
            params = {
                "tenant_id": filters.tenant_id,
                "embedding": json.dumps(query_embedding),
                "min_similarity": 1 - 0.75,  # Convert to distance (lower is better)
                "top_k": top_k,
            }

            if filters.date_from:
                params["date_from"] = filters.date_from
            if filters.date_to:
                params["date_to"] = filters.date_to
            if filters.document_types:
                params["doc_types"] = filters.document_types

            # Execute query
            statement = text(query_sql)
            rows = self.db.execute(statement, params).fetchall()

            # Map results
            for row in rows:
                result = SearchResult(
                    chunk_id=row[0],
                    document_id=row[1],
                    document_name=row[2],
                    chunk_text=row[3],
                    page_number=row[4],
                    chunk_type=row[5],
                    relevance_score=float(row[6]) if row[6] else 0.0,
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
    ) -> None:
        """Log search query for analytics and suggestions"""

        try:
            if self.db:
                from sqlalchemy import text
                import uuid

                # Check if document_search_log table exists
                # If not, just log to logger
                try:
                    insert_sql = """
                    INSERT INTO document_search_log
                    (search_id, tenant_id, query, results_count, execution_time_ms, created_at)
                    VALUES (:search_id, :tenant_id, :query, :results_count, :execution_time_ms, NOW())
                    """

                    params = {
                        "search_id": str(uuid.uuid4()),
                        "tenant_id": filters.tenant_id,
                        "query": query,
                        "results_count": results_count,
                        "execution_time_ms": execution_time_ms,
                    }

                    statement = text(insert_sql)
                    self.db.execute(statement, params)
                    self.db.commit()

                except Exception as table_error:
                    # Table may not exist, just log to logger
                    self.logger.warning(f"Could not log to DB: {str(table_error)}")

            self.logger.info(
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

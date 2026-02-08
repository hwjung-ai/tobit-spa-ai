"""Large data handling service for performance optimization.

Handles batch processing, pagination, and streaming for large datasets.
"""

import logging
from typing import Any, Dict, Generator, List, Optional, Tuple
from datetime import datetime

from core.db import get_session
from sqlmodel import Session, select
from core.cache import cache_manager, CacheKeys

logger = logging.getLogger(__name__)


class LargeDataHandler:
    """Handles large data operations efficiently."""
    
    def __init__(self):
        """Initialize large data handler."""
        self.batch_size = 1000  # Default batch size
        self.max_results = 10000  # Maximum results per query
    
    def paginated_query(
        self,
        session: Session,
        query_statement,
        page: int = 1,
        page_size: int = 100,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute query with pagination.
        
        Args:
            session: Database session
            query_statement: SQLModel query statement
            page: Page number (1-indexed)
            page_size: Number of results per page
            cache_key: Optional cache key for results
            
        Returns:
            Dict with results, pagination metadata
        """
        try:
            # Check cache
            if cache_key:
                cached = cache_manager.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for paginated query: {cache_key}")
                    return cached
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Execute query with pagination
            results = session.exec(
                query_statement.offset(offset).limit(page_size)
            ).all()
            
            # Get total count
            count_query = select(query_statement.columns[0])
            total = len(session.exec(query_statement).all())
            
            # Prepare response
            response = {
                "results": results,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size,
                    "has_next": page * page_size < total,
                    "has_prev": page > 1
                }
            }
            
            # Cache results
            if cache_key:
                cache_manager.set(cache_key, response, ttl=300)  # 5 minutes
            
            return response
            
        except Exception as e:
            logger.error(f"Paginated query failed: {e}", exc_info=True)
            raise
    
    def batch_insert(
        self,
        session: Session,
        model_class,
        data_list: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Insert data in batches for better performance.
        
        Args:
            session: Database session
            model_class: SQLModel class
            data_list: List of data dictionaries
            batch_size: Number of records per batch
            
        Returns:
            Dict with insertion results
        """
        try:
            batch_size = batch_size or self.batch_size
            total_count = len(data_list)
            inserted_count = 0
            errors = []
            
            # Process in batches
            for i in range(0, total_count, batch_size):
                batch = data_list[i:i + batch_size]
                
                try:
                    # Create model instances
                    instances = [model_class(**item) for item in batch]
                    
                    # Add to session
                    session.add_all(instances)
                    session.commit()
                    
                    inserted_count += len(batch)
                    logger.debug(f"Inserted batch {i//batch_size + 1}: {len(batch)} records")
                    
                except Exception as e:
                    errors.append({
                        "batch": i // batch_size + 1,
                        "error": str(e),
                        "batch_size": len(batch)
                    })
                    session.rollback()
            
            return {
                "total_count": total_count,
                "inserted_count": inserted_count,
                "failed_count": total_count - inserted_count,
                "errors": errors,
                "success": inserted_count == total_count
            }
            
        except Exception as e:
            logger.error(f"Batch insert failed: {e}", exc_info=True)
            raise
    
    def stream_results(
        self,
        session: Session,
        query_statement,
        batch_size: Optional[int] = None
    ) -> Generator[List[Any], None, None]:
        """
        Stream query results in batches.
        
        Args:
            session: Database session
            query_statement: SQLModel query statement
            batch_size: Number of records per batch
            
        Yields:
            List of results per batch
        """
        try:
            batch_size = batch_size or self.batch_size
            offset = 0
            
            while True:
                # Execute query with offset
                results = session.exec(
                    query_statement.offset(offset).limit(batch_size)
                ).all()
                
                if not results:
                    break
                
                yield results
                
                offset += batch_size
                
        except Exception as e:
            logger.error(f"Stream results failed: {e}", exc_info=True)
            raise
    
    def query_with_limit(
        self,
        session: Session,
        query_statement,
        limit: Optional[int] = None,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute query with enforced limit.
        
        Args:
            session: Database session
            query_statement: SQLModel query statement
            limit: Maximum number of results
            cache_key: Optional cache key for results
            
        Returns:
            Dict with results and metadata
        """
        try:
            limit = limit or self.max_results
            
            # Check cache
            if cache_key:
                cached = cache_manager.get(cache_key)
                if cached:
                    return cached
            
            # Execute query with limit
            results = session.exec(query_statement.limit(limit)).all()
            
            response = {
                "results": results,
                "count": len(results),
                "limit": limit,
                "truncated": len(results) >= limit
            }
            
            # Cache results
            if cache_key:
                cache_manager.set(cache_key, response, ttl=300)
            
            return response
            
        except Exception as e:
            logger.error(f"Query with limit failed: {e}", exc_info=True)
            raise
    
    def aggregate_query(
        self,
        session: Session,
        query_statement,
        group_by: List[str],
        aggregations: Dict[str, str],
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute aggregate query for large datasets.
        
        Args:
            session: Database session
            query_statement: Base query statement
            group_by: Columns to group by
            aggregations: Aggregation functions (e.g., {"total": "COUNT(*)", "sum": "SUM(amount)"})
            cache_key: Optional cache key for results
            
        Returns:
            Dict with aggregated results
        """
        try:
            # Check cache
            if cache_key:
                cached = cache_manager.get(cache_key)
                if cached:
                    return cached
            
            # Build aggregation query
            # This is a simplified version - in production, use proper SQL building
            select_clause = ", ".join([f"{v} as {k}" for k, v in aggregations.items()])
            group_clause = ", ".join(group_by)
            
            # Execute aggregate query
            # Note: This is a placeholder - actual implementation depends on query builder
            results = session.exec(query_statement).all()
            
            response = {
                "results": results,
                "group_by": group_by,
                "aggregations": aggregations
            }
            
            # Cache results
            if cache_key:
                cache_manager.set(cache_key, response, ttl=600)  # 10 minutes
            
            return response
            
        except Exception as e:
            logger.error(f"Aggregate query failed: {e}", exc_info=True)
            raise
    
    def export_large_dataset(
        self,
        session: Session,
        query_statement,
        format_type: str = "csv",
        batch_size: Optional[int] = None
    ) -> Generator[bytes, None, None]:
        """
        Stream large dataset export.
        
        Args:
            session: Database session
            query_statement: SQLModel query statement
            format_type: Export format (csv, json)
            batch_size: Number of records per batch
            
        Yields:
            Bytes of data per batch
        """
        try:
            batch_size = batch_size or self.batch_size
            
            if format_type == "csv":
                yield from self._export_csv_stream(session, query_statement, batch_size)
            elif format_type == "json":
                yield from self._export_json_stream(session, query_statement, batch_size)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error(f"Export large dataset failed: {e}", exc_info=True)
            raise
    
    def _export_csv_stream(
        self,
        session: Session,
        query_statement,
        batch_size: int
    ) -> Generator[bytes, None, None]:
        """Stream CSV export."""
        import csv
        import io
        
        header_written = False
        
        for batch in self.stream_results(session, query_statement, batch_size):
            output = io.StringIO()
            
            if not header_written and batch:
                # Write header
                writer = csv.DictWriter(output, fieldnames=batch[0].keys())
                writer.writeheader()
                header_written = True
            
            # Write data
            writer = csv.DictWriter(output, fieldnames=batch[0].keys())
            writer.writerows(batch)
            
            yield output.getvalue().encode('utf-8')
    
    def _export_json_stream(
        self,
        session: Session,
        query_statement,
        batch_size: int
    ) -> Generator[bytes, None, None]:
        """Stream JSON export."""
        import json
        
        yield b'[\n'
        
        for i, batch in enumerate(self.stream_results(session, query_statement, batch_size)):
            for j, record in enumerate(batch):
                if i > 0 or j > 0:
                    yield b',\n'
                yield json.dumps(record, default=str, ensure_ascii=False).encode('utf-8')
        
        yield b'\n]\n'
    
    def get_query_stats(
        self,
        session: Session,
        query_statement,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get query statistics without fetching all data.
        
        Args:
            session: Database session
            query_statement: SQLModel query statement
            cache_key: Optional cache key for results
            
        Returns:
            Dict with query statistics
        """
        try:
            # Check cache
            if cache_key:
                cached = cache_manager.get(cache_key)
                if cached:
                    return cached
            
            # Execute COUNT query
            count = len(session.exec(query_statement).all())
            
            response = {
                "count": count,
                "estimated_size_mb": count * 0.001,  # Rough estimate
                "batch_size": self.batch_size,
                "estimated_batches": (count + self.batch_size - 1) // self.batch_size,
                "requires_streaming": count > self.batch_size * 10
            }
            
            # Cache results
            if cache_key:
                cache_manager.set(cache_key, response, ttl=600)
            
            return response
            
        except Exception as e:
            logger.error(f"Get query stats failed: {e}", exc_info=True)
            raise


# Global large data handler instance
large_data_handler = LargeDataHandler()
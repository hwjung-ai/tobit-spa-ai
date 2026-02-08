"""Query autocomplete service for OPS queries.

Provides intelligent suggestions for SQL, Cypher, and natural language queries.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from core.db import get_session
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class QueryAutocompleter:
    """Provides query autocomplete suggestions."""
    
    def __init__(self):
        """Initialize autocompleter."""
        self.catalog_cache: Dict[str, Dict[str, Any]] = {}
        self.last_cache_update: Optional[float] = None
    
    def get_suggestions(
        self,
        query: str,
        cursor_position: int,
        query_type: str = "sql",
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get query suggestions based on cursor position.
        
        Args:
            query: Query string
            cursor_position: Cursor position in query
            query_type: Type of query (sql, cypher, natural)
            tenant_id: Tenant ID for catalog filtering
            
        Returns:
            Dict with suggestions
        """
        try:
            # Extract context before cursor
            context = query[:cursor_position]
            
            if query_type == "sql":
                return self._get_sql_suggestions(context, tenant_id)
            elif query_type == "cypher":
                return self._get_cypher_suggestions(context, tenant_id)
            elif query_type == "natural":
                return self._get_natural_language_suggestions(context, tenant_id)
            else:
                return {"suggestions": [], "context": context}
                
        except Exception as e:
            logger.error(f"Autocomplete failed: {e}", exc_info=True)
            return {"suggestions": [], "context": context}
    
    def _get_sql_suggestions(
        self,
        context: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get SQL query suggestions."""
        suggestions = []
        
        # Get catalog data
        catalog = self._get_catalog_data(tenant_id, "postgres")
        
        # Extract last word
        words = context.split()
        last_word = words[-1].upper() if words else ""
        second_last_word = words[-2].upper() if len(words) > 1 else ""
        
        # SQL keywords
        sql_keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN", 
            "INNER JOIN", "ON", "AND", "OR", "ORDER BY", "GROUP BY",
            "HAVING", "LIMIT", "OFFSET", "INSERT", "UPDATE", "DELETE",
            "CREATE", "DROP", "ALTER", "TABLE", "INDEX", "VIEW",
            "COUNT", "SUM", "AVG", "MIN", "MAX", "DISTINCT"
        ]
        
        # Suggest keywords
        if last_word and self._starts_with_case_insensitive(last_word, "SELECT"):
            suggestions.extend([
                {"type": "keyword", "text": "SELECT", "description": "Select columns from table"}
            ])
        
        # Suggest tables
        if second_last_word in ["FROM", "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN"]:
            tables = catalog.get("tables", [])
            for table in tables:
                if self._starts_with_case_insensitive(last_word, table["table_name"]):
                    suggestions.append({
                        "type": "table",
                        "text": table["table_name"],
                        "description": f"Table: {table['table_name']}",
                        "schema": table.get("schema_name", "public")
                    })
        
        # Suggest columns
        elif second_last_word not in sql_keywords:
            # Extract table name from context
            table_match = re.search(r'FROM\s+(\w+)', context, re.IGNORECASE)
            if table_match:
                table_name = table_match.group(1).upper()
                tables = catalog.get("tables", [])
                
                for table in tables:
                    if table["table_name"].upper() == table_name:
                        columns = table.get("columns", [])
                        for col in columns:
                            if self._starts_with_case_insensitive(last_word, col["column_name"]):
                                suggestions.append({
                                    "type": "column",
                                    "text": col["column_name"],
                                    "description": f"{col['column_name']} ({col['data_type']})",
                                    "table": table_name
                                })
                        break
        
        # Suggest functions
        if "SELECT" in context.upper():
            functions = [
                "COUNT(*)", "SUM(column)", "AVG(column)", "MIN(column)", 
                "MAX(column)", "DISTINCT column", "COUNT(DISTINCT column)"
            ]
            for func in functions:
                if self._starts_with_case_insensitive(last_word, func.split("(")[0]):
                    suggestions.append({
                        "type": "function",
                        "text": func,
                        "description": f"SQL aggregate function: {func}"
                    })
        
        return {
            "suggestions": suggestions[:20],  # Limit to 20 suggestions
            "context": context
        }
    
    def _get_cypher_suggestions(
        self,
        context: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get Cypher query suggestions."""
        suggestions = []
        
        # Get catalog data
        catalog = self._get_catalog_data(tenant_id, "neo4j")
        
        # Extract last word
        words = context.split()
        last_word = words[-1] if words else ""
        second_last_word = words[-2] if len(words) > 1 else ""
        
        # Cypher keywords
        cypher_keywords = [
            "MATCH", "WHERE", "RETURN", "LIMIT", "ORDER BY",
            "WITH", "CREATE", "DELETE", "SET", "MERGE",
            "OPTIONAL MATCH", "UNION", "UNION ALL"
        ]
        
        # Suggest labels
        if second_last_word in ["MATCH", "OPTIONAL MATCH", "CREATE", "MERGE"]:
            labels = catalog.get("labels", [])
            for label in labels:
                if self._starts_with_case_insensitive(last_word, label):
                    suggestions.append({
                        "type": "label",
                        "text": label,
                        "description": f"Node label: {label}"
                    })
        
        # Suggest properties
        if ":" in last_word:
            label_name = last_word.split(":")[0]
            labels = catalog.get("labels", [])
            
            for label in labels:
                if label.upper() == label_name.upper():
                    properties = label.get("properties", [])
                    for prop in properties:
                        suggestions.append({
                            "type": "property",
                            "text": prop["name"],
                            "description": f"{prop['name']} ({prop['type']})",
                            "label": label_name
                        })
                    break
        
        # Suggest relationships
        if "-[" in context or "]-" in context:
            relationships = catalog.get("relationships", [])
            for rel in relationships:
                if self._starts_with_case_insensitive(last_word, rel):
                    suggestions.append({
                        "type": "relationship",
                        "text": rel,
                        "description": f"Relationship: {rel}"
                    })
        
        return {
            "suggestions": suggestions[:20],
            "context": context
        }
    
    def _get_natural_language_suggestions(
        self,
        context: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get natural language query suggestions."""
        suggestions = []
        
        # Get catalog data for context
        catalog = self._get_catalog_data(tenant_id, "postgres")
        
        # Extract last word
        words = context.split()
        last_word = words[-1].lower() if words else ""
        
        # Suggest table names based on context
        tables = catalog.get("tables", [])
        
        # Common query patterns
        patterns = {
            "show": ["show", "list", "display"],
            "find": ["find", "search", "get", "retrieve"],
            "count": ["count", "how many", "number of"],
            "sum": ["sum", "total", "aggregate"],
            "avg": ["average", "mean", "avg"],
            "min": ["minimum", "min", "lowest"],
            "max": ["maximum", "max", "highest"]
        }
        
        # Match pattern and suggest tables
        for pattern, keywords in patterns.items():
            if any(kw in last_word for kw in keywords):
                for table in tables:
                    table_name = table["table_name"].lower()
                    if table_name.startswith(last_word) or self._fuzzy_match(last_word, table_name):
                        suggestions.append({
                            "type": "table",
                            "text": table_name,
                            "description": f"Table: {table['table_name']}",
                            "pattern": pattern
                        })
                break
        
        # Suggest common query templates
        templates = [
            {
                "type": "template",
                "text": "show all {table}",
                "description": "Show all records from a table",
                "parameters": ["table"]
            },
            {
                "type": "template",
                "text": "count {table} by {column}",
                "description": "Count records grouped by column",
                "parameters": ["table", "column"]
            },
            {
                "type": "template",
                "text": "find {table} where {column} = {value}",
                "description": "Find records matching condition",
                "parameters": ["table", "column", "value"]
            },
            {
                "type": "template",
                "text": "sum {column} from {table}",
                "description": "Sum column values",
                "parameters": ["column", "table"]
            }
        ]
        
        # Match templates
        for template in templates:
            if template["text"].startswith(last_word):
                suggestions.append(template)
        
        return {
            "suggestions": suggestions[:20],
            "context": context
        }
    
    def _get_catalog_data(
        self,
        tenant_id: str,
        db_type: str
    ) -> Dict[str, Any]:
        """Get catalog data with caching."""
        cache_key = f"{tenant_id}:{db_type}"
        
        # Return cached data if available
        if cache_key in self.catalog_cache:
            return self.catalog_cache[cache_key]
        
        # Load from database
        try:
            with Session(get_session()) as session:
                if db_type == "postgres":
                    return self._load_postgres_catalog(session, tenant_id)
                elif db_type == "neo4j":
                    return self._load_neo4j_catalog(session, tenant_id)
                else:
                    return {"tables": [], "labels": [], "relationships": []}
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}", exc_info=True)
            return {"tables": [], "labels": [], "relationships": []}
    
    def _load_postgres_catalog(
        self,
        session: Session,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Load PostgreSQL catalog."""
        # Query database catalog tables
        result = session.exec("""
            SELECT 
                table_schema as schema_name,
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_schema = t.table_schema AND table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)
        
        tables = []
        for row in result:
            # Get columns for this table
            columns = session.exec("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = :schema_name AND table_name = :table_name
                ORDER BY ordinal_position
            """, {"schema_name": row.schema_name, "table_name": row.table_name})
            
            tables.append({
                "schema_name": row.schema_name,
                "table_name": row.table_name,
                "column_count": row.column_count,
                "columns": [
                    {
                        "column_name": col.column_name,
                        "data_type": col.data_type,
                        "is_nullable": col.is_nullable,
                        "default": col.column_default
                    }
                    for col in columns
                ]
            })
        
        return {"tables": tables}
    
    def _load_neo4j_catalog(
        self,
        session: Session,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Load Neo4j catalog."""
        # This would query Neo4j for labels and relationships
        # For now, return empty structure
        return {
            "labels": [],
            "relationships": []
        }
    
    @staticmethod
    def _starts_with_case_insensitive(
        text: str,
        prefix: str
    ) -> bool:
        """Check if text starts with prefix (case insensitive)."""
        return text.upper().startswith(prefix.upper())
    
    @staticmethod
    def _fuzzy_match(query: str, target: str) -> bool:
        """Simple fuzzy matching."""
        if len(query) < 2:
            return False
        
        # Check if query is substring of target
        return query.lower() in target.lower()
    
    def clear_cache(self):
        """Clear catalog cache."""
        self.catalog_cache.clear()
        self.last_cache_update = None


# Global autocompleter instance
query_autocompleter = QueryAutocompleter()
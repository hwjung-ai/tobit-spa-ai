"""
SQL Template Processor for dynamic query generation.

This module processes SQL templates with placeholders like {where_clause}
and replaces them with actual SQL conditions based on parameters.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class SQLTemplateProcessor:
    """
    Process SQL templates with placeholder substitution.

    Handles:
    - {where_clause}: Dynamic WHERE conditions from filters
    - %(name)s: Named parameter placeholders (psycopg format)
    - %s: Positional placeholders
    """

    # SQL injection keywords to block
    DANGEROUS_KEYWORDS = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
        "TRUNCATE", "EXEC", "EXECUTE", "SCRIPT", "JAVASCRIPT"
    ]

    @staticmethod
    def _sanitize_identifier(identifier: str) -> str:
        """
        Sanitize SQL identifier (table/column name).

        Args:
            identifier: Identifier to sanitize

        Returns:
            Sanitized identifier (alphanumeric and underscore only)
        """
        # Remove any non-alphanumeric characters except underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)
        return sanitized

    @staticmethod
    def _validate_param_value(value: Any) -> bool:
        """
        Validate parameter value to prevent SQL injection.

        Args:
            value: Value to validate

        Returns:
            True if safe, False if potentially dangerous
        """
        if isinstance(value, str):
            upper_value = value.upper()
            for keyword in SQLTemplateProcessor.DANGEROUS_KEYWORDS:
                if keyword in upper_value:
                    logger.warning(f"Potentially dangerous keyword detected: {keyword}")
                    return False
        return True

    @staticmethod
    def build_where_clause(filters: List[Dict[str, Any]]) -> Tuple[str, List[Any]]:
        """
        Build WHERE clause from filter specifications.

        Args:
            filters: List of filter dicts with format:
                {"field": "column_name", "op": "operator", "value": "value"}

        Returns:
            Tuple of (where_clause_sql, params_list)

        Supported operators:
            - "=": equality
            - "!=": inequality
            - ">": greater than
            - "<": less than
            - ">=": greater or equal
            - "<=": less or equal
            - "like": LIKE pattern matching
            - "in": IN list
            "is_null": IS NULL
            "is_not_null": IS NOT NULL
        """
        if not filters:
            return "1=1", []

        conditions = []
        params = []

        for filter_spec in filters:
            field = filter_spec.get("field", "")
            operator = filter_spec.get("op", "=")
            value = filter_spec.get("value")

            # Sanitize field name
            field = SQLTemplateProcessor._sanitize_identifier(field)

            # Validate value
            if value is not None and not SQLTemplateProcessor._validate_param_value(value):
                logger.warning(f"Skipping potentially dangerous filter: {field} {operator} {value}")
                continue

            # Build condition based on operator
            if operator == "=":
                conditions.append(f"{field} = %s")
                params.append(value)
            elif operator == "!=":
                conditions.append(f"{field} != %s")
                params.append(value)
            elif operator == ">":
                conditions.append(f"{field} > %s")
                params.append(value)
            elif operator == "<":
                conditions.append(f"{field} < %s")
                params.append(value)
            elif operator == ">=":
                conditions.append(f"{field} >= %s")
                params.append(value)
            elif operator == "<=":
                conditions.append(f"{field} <= %s")
                params.append(value)
            elif operator == "like":
                conditions.append(f"{field} LIKE %s")
                params.append(value)
            elif operator == "in":
                if isinstance(value, (list, tuple)):
                    placeholders = ", ".join(["%s"] * len(value))
                    conditions.append(f"{field} IN ({placeholders})")
                    params.extend(value)
            elif operator == "is_null":
                conditions.append(f"{field} IS NULL")
            elif operator == "is_not_null":
                conditions.append(f"{field} IS NOT NULL")
            else:
                logger.warning(f"Unknown operator: {operator}, skipping filter")

        if not conditions:
            return "1=1", []

        where_clause = " AND ".join(conditions)
        return where_clause, params

    @staticmethod
    def process_template(
        sql: str,
        params: Dict[str, Any]
    ) -> Tuple[str, Tuple[Any, ...]]:
        """
        Process SQL template with placeholder substitution.

        Args:
            sql: SQL template string with potential {where_clause} placeholder
            params: Parameters dict that may contain:
                - tenant_id: Tenant ID for multi-tenancy
                - filters: List of filter specs for {where_clause}
                - query_params: Direct query parameters
                - Other key-value pairs for parameter substitution

        Returns:
            Tuple of (processed_sql, params_tuple)

        Examples:
            >>> sql = "SELECT * FROM ci WHERE ci.tenant_id = %s AND {where_clause}"
            >>> params = {"tenant_id": "t1", "filters": [{"field": "status", "op": "=", "value": "active"}]}
            >>> processed_sql, params_tuple = process_template(sql, params)
            >>> processed_sql
            'SELECT * FROM ci WHERE ci.tenant_id = %s AND status = %s'
            >>> params_tuple
            ('t1', 'active')
        """
        processed_sql = sql
        all_params = []

        # Add tenant_id as first parameter if present
        tenant_id = params.get("tenant_id")
        if tenant_id:
            all_params.append(tenant_id)

        # Extract filters for where_clause substitution
        filters = params.get("filters", [])
        where_clause, where_params = SQLTemplateProcessor.build_where_clause(filters)
        all_params.extend(where_params)

        # Replace {where_clause} placeholder (ALWAYS replace, even with empty filters)
        if "{where_clause}" in processed_sql:
            processed_sql = processed_sql.replace("{where_clause}", where_clause)
        elif "{where}" in processed_sql:
            processed_sql = processed_sql.replace("{where}", where_clause)

        # Replace {direction} placeholder (used after {order_by})
        if "{direction}" in processed_sql:
            order_dir = params.get("order_dir", "ASC")
            order_dir = "ASC" if order_dir.upper() == "ASC" else "DESC"
            processed_sql = processed_sql.replace("{direction}", order_dir)

        # Extract other query parameters
        query_params = params.get("query_params", {})
        if query_params:
            # Add query_params to all_params
            for key, value in query_params.items():
                if key not in ["filters", "limit", "offset", "order_by", "tenant_id"]:
                    all_params.append(value)

        # Handle limit, offset, order_by placeholders
        if "{limit}" in processed_sql:
            limit = params.get("limit", 100)
            processed_sql = processed_sql.replace("{limit}", str(limit))

        if "{offset}" in processed_sql:
            offset = params.get("offset", 0)
            processed_sql = processed_sql.replace("{offset}", str(offset))

        if "{order_by}" in processed_sql:
            order_by = params.get("order_by", "ci_code")
            order_by = SQLTemplateProcessor._sanitize_identifier(order_by)
            # Don't include order_dir here - {direction} should be in SQL
            processed_sql = processed_sql.replace("{order_by}", order_by)

        # If no where clause placeholder was found but we have filters,
        # append WHERE clause to existing query
        if "{where_clause}" not in sql and "{where}" not in sql and filters:
            where_clause, where_params = SQLTemplateProcessor.build_where_clause(filters)
            if where_clause != "1=1":
                # Check if SQL already has WHERE clause
                if " WHERE " in processed_sql.upper():
                    processed_sql = f"{processed_sql} AND {where_clause}"
                else:
                    processed_sql = f"{processed_sql} WHERE {where_clause}"
                all_params.extend(where_params)

        # If no where clause placeholder was found but we have filters,
        # append WHERE clause to existing query
        if "{where_clause}" not in sql and "{where}" not in sql and filters:
            where_clause, where_params = SQLTemplateProcessor.build_where_clause(filters)
            if where_clause != "1=1":
                # Check if SQL already has WHERE clause
                if " WHERE " in processed_sql.upper():
                    processed_sql = f"{processed_sql} AND {where_clause}"
                else:
                    processed_sql = f"{processed_sql} WHERE {where_clause}"
                all_params.extend(where_params)

        # Handle LIMIT %s pattern - add limit value to params if present
        if "LIMIT %s" in processed_sql.upper() or "LIMIT %s" in processed_sql:
            limit_value = params.get("limit")
            if limit_value is not None:
                all_params.append(int(limit_value))

        # Convert params list to tuple for psycopg
        params_tuple = tuple(all_params) if all_params else ()

        return processed_sql, params_tuple

    @staticmethod
    def extract_placeholder_count(sql: str) -> int:
        """
        Count the number of %s placeholders in SQL.

        Args:
            sql: SQL string

        Returns:
            Number of %s placeholders
        """
        return sql.count("%s")

    @staticmethod
    def validate_param_count(sql: str, params: Tuple[Any, ...]) -> bool:
        """
        Validate that parameter count matches placeholder count.

        Args:
            sql: SQL string with %s placeholders
            params: Parameters tuple

        Returns:
            True if counts match, False otherwise
        """
        placeholder_count = SQLTemplateProcessor.extract_placeholder_count(sql)
        param_count = len(params) if params else 0

        if placeholder_count != param_count:
            logger.error(
                f"Parameter count mismatch: SQL has {placeholder_count} placeholders, "
                f"but {param_count} parameters provided"
            )
            return False

        return True

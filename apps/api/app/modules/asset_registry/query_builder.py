"""
Schema-based Query Builder
Builds SQL queries dynamically using schema assets instead of hardcoded SQL.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from core.db import get_session_context
from sqlmodel import select

from app.modules.asset_registry.loader import load_schema_asset
from app.modules.asset_registry.models import TbAssetRegistry

logger = logging.getLogger(__name__)


class SchemaQueryBuilder:
    """Builds SQL queries using schema assets"""

    def __init__(self, schema_asset_name: str = "primary_postgres_schema"):
        self.schema_asset_name = schema_asset_name
        self._schema: dict[str, Any] | None = None
        self._table_schemas: dict[str, dict[str, Any]] = {}

    def _load_schema(self) -> dict[str, Any]:
        """Load schema asset"""
        if self._schema is None:
            schema_payload = load_schema_asset(self.schema_asset_name)
            if not schema_payload:
                raise ValueError(f"Schema asset not found: {self.schema_asset_name}")

            self._schema = schema_payload.get("catalog", {})

            # Build table schema lookup
            if isinstance(self._schema, dict):
                for table_name, table_data in self._schema.items():
                    if isinstance(table_data, dict) and "columns" in table_data:
                        self._table_schemas[table_name] = table_data

        return self._schema

    @property
    def schema(self) -> dict[str, Any]:
        """Get schema (lazy load)"""
        if self._schema is None:
            self._load_schema()
        return self._schema or {}

    @property
    def table_schemas(self) -> dict[str, dict[str, Any]]:
        """Get table schemas"""
        if not self._table_schemas:
            self._load_schema()
        return self._table_schemas

    def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
        """Get column definitions for a table"""
        table_schema = self.table_schemas.get(table_name, {})
        return table_schema.get("columns", [])

    def get_column_names(self, table_name: str) -> list[str]:
        """Get column names for a table"""
        columns = self.get_table_columns(table_name)
        return [col["name"] for col in columns if isinstance(col, dict) and "name" in col]

    def get_column_type(self, table_name: str, column_name: str) -> str | None:
        """Get column data type"""
        columns = self.get_table_columns(table_name)
        for col in columns:
            if col.get("name") == column_name:
                return col.get("type")
        return None

    def has_column(self, table_name: str, column_name: str) -> bool:
        """Check if table has column"""
        return column_name in self.get_column_names(table_name)

    def build_select(
        self,
        table_name: str,
        columns: list[str] | None = None,
        where_clause: str | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        joins: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Build SELECT query using schema.

        Args:
            table_name: Main table name
            columns: Column names to select (None = all)
            where_clause: WHERE clause conditions
            order_by: ORDER BY clause
            limit: LIMIT value
            offset: OFFSET value
            joins: List of join dicts with keys: table, on, type (LEFT/INNER)

        Returns:
            Complete SQL query
        """
        # Validate table exists in schema
        if table_name not in self.table_schemas:
            logger.warning(f"Table {table_name} not in schema, building query anyway")

        # SELECT clause
        if columns:
            # Validate columns exist
            valid_columns = []
            all_columns = self.get_column_names(table_name)
            for col in columns:
                if "." in col:  # qualified column like "ci.ci_id"
                    valid_columns.append(col)
                elif col in all_columns:
                    valid_columns.append(f"{table_name}.{col}")
                else:
                    logger.warning(f"Column {col} not found in {table_name}")
            select_clause = ", ".join(valid_columns) if valid_columns else f"{table_name}.*"
        else:
            select_clause = f"{table_name}.*"

        # FROM clause
        query_parts = [f"SELECT {select_clause}", f"FROM {table_name}"]

        # JOINs
        if joins:
            for join in joins:
                join_table = join.get("table")
                join_on = join.get("on", "")
                join_type = join.get("type", "LEFT")
                if join_table and join_on:
                    query_parts.append(f"{join_type} JOIN {join_table} ON {join_on}")

        # WHERE clause
        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        # ORDER BY
        if order_by:
            query_parts.append(f"ORDER BY {order_by}")

        # LIMIT
        if limit is not None:
            query_parts.append(f"LIMIT {int(limit)}")

        # OFFSET
        if offset is not None:
            query_parts.append(f"OFFSET {int(offset)}")

        return "\n".join(query_parts)

    def build_aggregate(
        self,
        table_name: str,
        group_by: list[str] | None = None,
        metrics: list[dict[str, str]] | None = None,
        where_clause: str | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Build aggregate query using schema.

        Args:
            table_name: Main table name
            group_by: Columns to group by
            metrics: List of metric dicts with keys: column, agg (count/sum/avg/max/min), alias
            where_clause: WHERE clause
            order_by: ORDER BY clause
            limit: LIMIT value

        Returns:
            Complete SQL query
        """
        # SELECT clause: group columns + metrics
        select_parts = []

        if group_by:
            for col in group_by:
                if "." in col:
                    select_parts.append(col)
                else:
                    select_parts.append(f"{table_name}.{col}")
        else:
            select_parts.append(f"{table_name}.*")

        # Add metrics
        if metrics:
            for metric in metrics:
                col = metric.get("column", "*")
                agg = metric.get("agg", "count").upper()
                alias = metric.get("alias")

                # Validate column exists
                if col != "*" and not self.has_column(table_name, col):
                    logger.warning(f"Column {col} not found in {table_name} for aggregate")

                metric_expr = f"{agg}({col})"
                if alias:
                    metric_expr += f" AS {alias}"
                select_parts.append(metric_expr)

        select_clause = ", ".join(select_parts)

        query_parts = [f"SELECT {select_clause}", f"FROM {table_name}"]

        # WHERE
        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        # GROUP BY
        if group_by:
            group_cols = [f"{table_name}.{col}" if "." not in col else col for col in group_by]
            query_parts.append(f"GROUP BY {', '.join(group_cols)}")

        # ORDER BY
        if order_by:
            query_parts.append(f"ORDER BY {order_by}")

        # LIMIT
        if limit is not None:
            query_parts.append(f"LIMIT {int(limit)}")

        return "\n".join(query_parts)

    def build_count(self, table_name: str, where_clause: str | None = None) -> str:
        """Build COUNT query"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        return query

    def get_primary_key(self, table_name: str) -> str | None:
        """Get primary key column for table (from schema inspection)"""
        columns = self.get_table_columns(table_name)
        # Common patterns
        for col in columns:
            name = col.get("name", "")
            if name.endswith("_id") or name == "id":
                return name
        # First column fallback
        if columns:
            return columns[0].get("name")
        return None


# Global instance
_query_builder: SchemaQueryBuilder | None = None


def get_query_builder(schema_asset_name: str = "primary_postgres_schema") -> SchemaQueryBuilder:
    """Get global query builder instance"""
    global _query_builder
    if _query_builder is None or _query_builder.schema_asset_name != schema_asset_name:
        _query_builder = SchemaQueryBuilder(schema_asset_name)
    return _query_builder

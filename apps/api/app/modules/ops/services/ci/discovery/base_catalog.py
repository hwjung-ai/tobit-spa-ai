"""
Base Catalog - Abstract base class for database schema introspection.

This module provides the abstract interface for all database-specific schema discovery implementations.
Supports PostgreSQL, MySQL, Oracle, SQL Server, and other databases through implementation of this interface.
"""

from abc import ABC, abstractmethod


class BaseCatalog(ABC):
    """Base class for database schema introspection"""

    def __init__(self, source_asset: dict):
        """
        Initialize catalog with source asset configuration.

        Args:
            source_asset: Source Asset dict with connection configuration
        """
        self.source_asset = source_asset
        self.connection = None

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection"""
        pass

    @abstractmethod
    async def fetch_tables(self, schema_names: list[str] | None = None) -> list[dict]:
        """
        Fetch table list from database.

        Returns:
            List of dicts with keys: table_name, schema_name, comment
        """
        pass

    @abstractmethod
    async def fetch_columns(self, table_name: str, schema_name: str | None = None) -> list[dict]:
        """
        Fetch column metadata for a table.

        Returns:
            List of dicts with keys: column_name, data_type, is_nullable, default_value, comment
        """
        pass

    @abstractmethod
    async def fetch_primary_keys(self, table_name: str, schema_name: str | None = None) -> list[str]:
        """Fetch primary key column names"""
        pass

    @abstractmethod
    async def fetch_foreign_keys(self, table_name: str, schema_name: str | None = None) -> list[dict]:
        """
        Fetch foreign key constraints.

        Returns:
            List of dicts with keys: column, ref_table, ref_column
        """
        pass

    @abstractmethod
    async def fetch_indexes(self, table_name: str, schema_name: str | None = None) -> list[dict]:
        """
        Fetch index information.

        Returns:
            List of dicts with keys: name, definition
        """
        pass

    async def fetch_row_count(self, table_name: str, schema_name: str | None = None) -> int:
        """
        Fetch table row count (optional, can be slow for large tables).

        Returns:
            Number of rows in table
        """
        return 0

    async def build_catalog(self, schema_names: list[str] | None = None) -> dict:
        """
        Build complete schema catalog for specified schemas.

        Args:
            schema_names: List of schema names to scan (None = default schema)

        Returns:
            Dict with keys: tables, database_type
        """
        await self.connect()

        tables_data = []

        # Fetch all tables
        all_tables = await self.fetch_tables(schema_names)

        for table_info in all_tables:
            table_name = table_info["table_name"]
            schema_name = table_info.get("schema_name", "public")

            try:
                # Fetch columns
                columns = await self.fetch_columns(table_name, schema_name)

                # Fetch primary keys
                pk_columns = await self.fetch_primary_keys(table_name, schema_name)

                # Fetch foreign keys
                fk_info = await self.fetch_foreign_keys(table_name, schema_name)

                # Fetch indexes
                indexes = await self.fetch_indexes(table_name, schema_name)

                # Optional: row count
                row_count = await self.fetch_row_count(table_name, schema_name)

                tables_data.append({
                    "name": table_name,
                    "schema_name": schema_name,
                    "comment": table_info.get("comment"),
                    "columns": self._enrich_columns(columns, pk_columns, fk_info),
                    "indexes": indexes,
                    "row_count": row_count if row_count > 0 else None,
                    "enabled": True,  # Default to enabled
                })
            except Exception as e:
                # Log error but continue scanning other tables
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to fetch metadata for table {schema_name}.{table_name}: {e}")
                continue

        return {
            "tables": tables_data,
            "database_type": self.get_database_type(),
        }

    def _enrich_columns(
        self,
        columns: list[dict],
        pk_columns: list[str],
        fk_info: list[dict],
    ) -> list[dict]:
        """
        Enrich column data with PK/FK information.

        Args:
            columns: Base column metadata
            pk_columns: List of primary key column names
            fk_info: List of foreign key info dicts

        Returns:
            Enriched column list
        """
        enriched = []

        for col in columns:
            col["is_primary_key"] = col["column_name"] in pk_columns

            # Find FK reference
            fk_ref = next(
                (fk for fk in fk_info if fk["column"] == col["column_name"]),
                None,
            )
            if fk_ref:
                col["is_foreign_key"] = True
                col["foreign_key_table"] = fk_ref["ref_table"]
                col["foreign_key_column"] = fk_ref["ref_column"]
            else:
                col["is_foreign_key"] = False
                col["foreign_key_table"] = None
                col["foreign_key_column"] = None

            enriched.append(col)

        return enriched

    @abstractmethod
    def get_database_type(self) -> str:
        """Return database type identifier (e.g., 'postgresql', 'mysql', 'oracle')"""
        pass

    async def close(self):
        """Close database connection"""
        if self.connection:
            try:
                await self.connection.close()
            except Exception:
                pass

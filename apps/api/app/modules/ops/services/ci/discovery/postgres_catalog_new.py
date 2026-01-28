"""
PostgreSQL Catalog - PostgreSQL schema introspection implementation.

This module implements schema discovery for PostgreSQL databases,
extracting table, column, and constraint metadata.
"""

import asyncio
from typing import Any, Optional

from .base_catalog import BaseCatalog

try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    AsyncConnection = None


class PostgresCatalog(BaseCatalog):
    """PostgreSQL database schema introspection"""

    def get_database_type(self) -> str:
        return "postgresql"

    async def connect(self) -> None:
        """Establish PostgreSQL connection using psycopg async driver"""
        if not AsyncConnection:
            raise ImportError("psycopg is required for PostgreSQL catalog discovery")

        conn_config = self.source_asset.get("connection", {})

        # Resolve password from multiple sources
        password = self._resolve_password(conn_config)

        self.connection = await AsyncConnection.connect(
            host=conn_config.get("host", "localhost"),
            port=conn_config.get("port", 5432),
            user=conn_config.get("username", "postgres"),
            password=password,
            dbname=conn_config.get("database"),
            connect_timeout=conn_config.get("timeout", 30),
        )

    def _resolve_password(self, conn_config: dict) -> str | None:
        """Resolve password from multiple sources"""
        import os

        # Priority: secret_key_ref > password_encrypted > password
        secret_key_ref = conn_config.get("secret_key_ref")
        if secret_key_ref and secret_key_ref.startswith("env:"):
            env_var = secret_key_ref.split("env:", 1)[1]
            return os.environ.get(env_var)

        if conn_config.get("password_encrypted"):
            # TODO: Decrypt using EncryptionManager
            return conn_config.get("password_encrypted")

        return conn_config.get("password")

    async def fetch_tables(self, schema_names: list[str] | None = None) -> list[dict]:
        """Fetch table list from information_schema"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        if schema_names is None:
            schema_names = ["public"]

        query = """
            SELECT
                table_schema,
                table_name,
                obj_description((table_schema || '.' || table_name)::regclass, 'pg_class') as comment
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema = ANY(%s)
            ORDER BY table_schema, table_name
        """

        try:
            result = await self.connection.execute(query, (schema_names,))
            rows = await result.fetchall()

            return [
                {
                    "schema_name": row[0],
                    "table_name": row[1],
                    "comment": row[2],
                }
                for row in rows
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch tables: {e}")

    async def fetch_columns(self, table_name: str, schema_name: str | None = None) -> list[dict]:
        """Fetch column metadata for a table"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        schema_name = schema_name or "public"

        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                col_description((table_schema || '.' || table_name)::regclass, ordinal_position) as comment
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """

        try:
            result = await self.connection.execute(query, (schema_name, table_name))
            rows = await result.fetchall()

            return [
                {
                    "column_name": row[0],
                    "data_type": row[1],
                    "is_nullable": row[2] == "YES",
                    "default_value": row[3],
                    "comment": row[4],
                }
                for row in rows
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch columns for table {table_name}: {e}")

    async def fetch_primary_keys(self, table_name: str, schema_name: str | None = None) -> list[str]:
        """Fetch primary key column names"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        schema_name = schema_name or "public"

        query = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = (%s || '.' || %s)::regclass
              AND i.indisprimary
        """

        try:
            result = await self.connection.execute(query, (schema_name, table_name))
            rows = await result.fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch primary keys for {table_name}: {e}")

    async def fetch_foreign_keys(self, table_name: str, schema_name: str | None = None) -> list[dict]:
        """Fetch foreign key constraints"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        schema_name = schema_name or "public"

        query = """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s
        """

        try:
            result = await self.connection.execute(query, (schema_name, table_name))
            rows = await result.fetchall()

            return [
                {
                    "column": row[0],
                    "ref_table": row[1],
                    "ref_column": row[2],
                }
                for row in rows
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch foreign keys for {table_name}: {e}")

    async def fetch_indexes(self, table_name: str, schema_name: str | None = None) -> list[dict]:
        """Fetch index information"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        schema_name = schema_name or "public"

        query = """
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = %s AND tablename = %s
        """

        try:
            result = await self.connection.execute(query, (schema_name, table_name))
            rows = await result.fetchall()

            return [
                {
                    "name": row[0],
                    "definition": row[1],
                }
                for row in rows
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch indexes for {table_name}: {e}")

    async def fetch_row_count(self, table_name: str, schema_name: str | None = None) -> int:
        """Fetch table row count (can be slow for large tables)"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        schema_name = schema_name or "public"

        try:
            # Use safe table/schema name by quoting
            query = f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"'
            result = await self.connection.execute(query)
            row = await result.fetchone()
            return row[0] if row else 0
        except Exception as e:
            # Row count is optional - return 0 on failure
            return 0

    async def close(self):
        """Close PostgreSQL connection"""
        if self.connection:
            try:
                await self.connection.close()
            except Exception:
                pass
            self.connection = None

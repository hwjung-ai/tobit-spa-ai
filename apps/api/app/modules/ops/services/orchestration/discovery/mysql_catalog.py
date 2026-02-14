"""
MySQL Catalog - MySQL schema introspection implementation.

This module implements schema discovery for MySQL/MariaDB databases,
extracting table, column, and constraint metadata.

Status:
- Sample/reference implementation in this project.
- Not currently used by default production flow.
"""

from .base_catalog import BaseCatalog

try:
    import aiomysql
except ImportError:
    aiomysql = None


class MySQLCatalog(BaseCatalog):
    """MySQL/MariaDB schema introspection (sample/reference implementation)."""

    def get_database_type(self) -> str:
        return "mysql"

    async def connect(self) -> None:
        """Establish MySQL connection using aiomysql"""
        if not aiomysql:
            raise ImportError("aiomysql is required for MySQL catalog discovery")

        conn_config = self.source_asset.get("connection", {})
        password = self._resolve_password(conn_config)

        self.connection = await aiomysql.connect(
            host=conn_config.get("host", "localhost"),
            port=conn_config.get("port", 3306),
            user=conn_config.get("username", "root"),
            password=password,
            db=conn_config.get("database"),
            connect_timeout=conn_config.get("timeout", 30),
        )

    def _resolve_password(self, conn_config: dict) -> str | None:
        """Resolve password from multiple sources"""
        import logging
        import os

        _logger = logging.getLogger(__name__)

        secret_key_ref = conn_config.get("secret_key_ref")
        if secret_key_ref and secret_key_ref.startswith("env:"):
            env_var = secret_key_ref.split("env:", 1)[1]
            return os.environ.get(env_var)

        if conn_config.get("password_encrypted"):
            try:
                from core.encryption import get_encryption_manager
                manager = get_encryption_manager()
                return manager.decrypt(conn_config["password_encrypted"])
            except Exception as e:
                _logger.error(f"Failed to decrypt password_encrypted: {e}")
                return None

        return conn_config.get("password")

    async def fetch_tables(self, schema_names: list[str] | None = None) -> list[dict]:
        """Fetch table list from MySQL information_schema"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        database = schema_names[0] if schema_names else self.source_asset["connection"]["database"]

        query = """
            SELECT
                TABLE_SCHEMA,
                TABLE_NAME,
                TABLE_COMMENT
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, (database,))
                rows = await cursor.fetchall()

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

        database = schema_name or self.source_asset["connection"]["database"]

        query = """
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COLUMN_COMMENT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, (database, table_name))
                rows = await cursor.fetchall()

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

        database = schema_name or self.source_asset["connection"]["database"]

        query = """
            SELECT COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
              AND CONSTRAINT_NAME = 'PRIMARY'
        """

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, (database, table_name))
                rows = await cursor.fetchall()

            return [row[0] for row in rows]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch primary keys for {table_name}: {e}")

    async def fetch_foreign_keys(self, table_name: str, schema_name: str | None = None) -> list[dict]:
        """Fetch foreign key constraints"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        database = schema_name or self.source_asset["connection"]["database"]

        query = """
            SELECT
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL
        """

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, (database, table_name))
                rows = await cursor.fetchall()

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

        database = schema_name or self.source_asset["connection"]["database"]

        query = """
            SELECT
                INDEX_NAME,
                CONCAT('INDEX ', INDEX_NAME, ' ON ', TABLE_NAME, ' (', GROUP_CONCAT(COLUMN_NAME), ')')
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            GROUP BY INDEX_NAME
        """

        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, (database, table_name))
                rows = await cursor.fetchall()

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

        database = schema_name or self.source_asset["connection"]["database"]

        try:
            query = "SELECT TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s"
            async with self.connection.cursor() as cursor:
                await cursor.execute(query, (database, table_name))
                row = await cursor.fetchone()
                return row[0] if row and row[0] else 0
        except Exception:
            # Row count is optional - return 0 on failure
            return 0

    async def close(self):
        """Close MySQL connection"""
        if self.connection:
            try:
                self.connection.close()
                await self.connection.wait_closed()
            except Exception:
                pass
            self.connection = None

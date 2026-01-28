"""
Oracle Catalog - Oracle database schema introspection implementation.

This module implements schema discovery for Oracle databases,
extracting table, column, and constraint metadata.
"""

from .base_catalog import BaseCatalog

try:
    import oracledb
except ImportError:
    oracledb = None


class OracleCatalog(BaseCatalog):
    """Oracle database schema introspection"""

    def get_database_type(self) -> str:
        return "oracle"

    async def connect(self) -> None:
        """Establish Oracle connection using oracledb driver"""
        if not oracledb:
            raise ImportError("oracledb is required for Oracle catalog discovery")

        conn_config = self.source_asset.get("connection", {})
        password = self._resolve_password(conn_config)

        # Oracle uses synchronous driver, not async
        # We'll wrap it but keep it synchronous
        dsn = conn_config.get("dsn") or (
            f"{conn_config.get('host', 'localhost')}:"
            f"{conn_config.get('port', 1521)}/"
            f"{conn_config.get('database')}"
        )

        try:
            self.connection = oracledb.connect(
                user=conn_config.get("username"),
                password=password,
                dsn=dsn,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Oracle: {e}")

    def _resolve_password(self, conn_config: dict) -> str | None:
        """Resolve password from multiple sources"""
        import os

        secret_key_ref = conn_config.get("secret_key_ref")
        if secret_key_ref and secret_key_ref.startswith("env:"):
            env_var = secret_key_ref.split("env:", 1)[1]
            return os.environ.get(env_var)

        if conn_config.get("password_encrypted"):
            return conn_config.get("password_encrypted")

        return conn_config.get("password")

    async def fetch_tables(self, schema_names: list[str] | None = None) -> list[dict]:
        """Fetch table list from Oracle ALL_TABLES"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        # Oracle uses owner/schema concept
        owner = schema_names[0].upper() if schema_names else self.source_asset["connection"]["username"].upper()

        query = """
            SELECT
                OWNER,
                TABLE_NAME,
                (SELECT COMMENTS FROM ALL_TAB_COMMENTS WHERE OWNER = t.OWNER AND TABLE_NAME = t.TABLE_NAME)
            FROM ALL_TABLES t
            WHERE OWNER = :owner
            ORDER BY TABLE_NAME
        """

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, {"owner": owner})
            rows = cursor.fetchall()

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

        owner = schema_name or self.source_asset["connection"]["username"].upper()
        table_name_upper = table_name.upper()

        query = """
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.NULLABLE,
                c.DATA_DEFAULT,
                cc.COMMENTS
            FROM ALL_TAB_COLUMNS c
            LEFT JOIN ALL_COL_COMMENTS cc
              ON c.OWNER = cc.OWNER
              AND c.TABLE_NAME = cc.TABLE_NAME
              AND c.COLUMN_NAME = cc.COLUMN_NAME
            WHERE c.OWNER = :owner AND c.TABLE_NAME = :table_name
            ORDER BY c.COLUMN_ID
        """

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, {"owner": owner, "table_name": table_name_upper})
            rows = cursor.fetchall()

            return [
                {
                    "column_name": row[0],
                    "data_type": row[1],
                    "is_nullable": row[2] == "Y",
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

        owner = schema_name or self.source_asset["connection"]["username"].upper()
        table_name_upper = table_name.upper()

        query = """
            SELECT cols.COLUMN_NAME
            FROM ALL_CONSTRAINTS cons
            JOIN ALL_CONS_COLUMNS cols
              ON cons.CONSTRAINT_NAME = cols.CONSTRAINT_NAME
              AND cons.OWNER = cols.OWNER
            WHERE cons.CONSTRAINT_TYPE = 'P'
              AND cons.OWNER = :owner
              AND cons.TABLE_NAME = :table_name
        """

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, {"owner": owner, "table_name": table_name_upper})
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch primary keys for {table_name}: {e}")

    async def fetch_foreign_keys(self, table_name: str, schema_name: str | None = None) -> list[dict]:
        """Fetch foreign key constraints"""
        if not self.connection:
            raise RuntimeError("Not connected to database")

        owner = schema_name or self.source_asset["connection"]["username"].upper()
        table_name_upper = table_name.upper()

        query = """
            SELECT
                cols.COLUMN_NAME,
                r_cons.TABLE_NAME,
                r_cols.COLUMN_NAME
            FROM ALL_CONSTRAINTS cons
            JOIN ALL_CONS_COLUMNS cols
              ON cons.CONSTRAINT_NAME = cols.CONSTRAINT_NAME
              AND cons.OWNER = cols.OWNER
            JOIN ALL_CONSTRAINTS r_cons
              ON cons.R_CONSTRAINT_NAME = r_cons.CONSTRAINT_NAME
              AND cons.R_OWNER = r_cons.OWNER
            JOIN ALL_CONS_COLUMNS r_cols
              ON r_cons.CONSTRAINT_NAME = r_cols.CONSTRAINT_NAME
              AND r_cons.OWNER = r_cols.OWNER
            WHERE cons.CONSTRAINT_TYPE = 'R'
              AND cons.OWNER = :owner
              AND cons.TABLE_NAME = :table_name
        """

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, {"owner": owner, "table_name": table_name_upper})
            rows = cursor.fetchall()

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

        owner = schema_name or self.source_asset["connection"]["username"].upper()
        table_name_upper = table_name.upper()

        query = """
            SELECT
                INDEX_NAME,
                'INDEX on ' || TABLE_NAME
            FROM ALL_INDEXES
            WHERE OWNER = :owner AND TABLE_NAME = :table_name
        """

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, {"owner": owner, "table_name": table_name_upper})
            rows = cursor.fetchall()

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

        owner = schema_name or self.source_asset["connection"]["username"].upper()
        table_name_upper = table_name.upper()

        try:
            query = f'SELECT COUNT(*) FROM "{owner}"."{table_name_upper}"'
            cursor = self.connection.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception:
            # Row count is optional - return 0 on failure
            return 0

    async def close(self):
        """Close Oracle connection"""
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

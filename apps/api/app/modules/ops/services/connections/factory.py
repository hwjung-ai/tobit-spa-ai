"""
ConnectionFactory - Dynamic connection creation for multiple source types.

This module implements the Factory pattern for creating connections to
different data sources based on source asset configuration.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict

from core.encryption import get_encryption_manager

from app.modules.ops.services.connections.sql_processor import SQLTemplateProcessor

logger = logging.getLogger(__name__)


class SourceConnection(ABC):
    """
    Abstract base class for source connections.

    Each source type (PostgreSQL, Neo4j, REST API, etc.) should implement
    this interface to provide a consistent execution interface.
    """

    def __init__(self, source_asset: Dict[str, Any]):
        """
        Initialize the connection with source asset configuration.

        Args:
            source_asset: Source asset dict containing connection details
        """
        self.source_asset = source_asset
        self.source_type = source_asset.get("source_type", "postgresql")
        self.connection = None

    @abstractmethod
    def connect(self) -> None:
        """
        Establish the connection to the data source.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def execute(
        self, query: str, params: Dict[str, Any] | None = None
    ) -> Any:
        """
        Execute a query against the data source.

        Args:
            query: Query string (SQL, Cypher, HTTP config, etc.)
            params: Optional query parameters

        Returns:
            Query result (format varies by source type)
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the connection and cleanup resources."""
        pass

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def _resolve_password(self) -> str:
        """
        Resolve password from connection config.

        Supports multiple password resolution methods:
        1. secret_key_ref: "env:VARIABLE_NAME" - read from environment variable
        2. password_encrypted - decrypt using EncryptionManager
        3. password - direct password (for testing)

        Returns:
            Resolved password string

        Raises:
            ValueError: If password cannot be resolved
        """
        conn_config = self.source_asset.get("connection", {})

        # Method 1: secret_key_ref (env:VARIABLE_NAME)
        secret_key_ref = conn_config.get("secret_key_ref")
        if secret_key_ref:
            if secret_key_ref.startswith("env:"):
                env_var = secret_key_ref[4:]  # Remove "env:" prefix
                password = os.getenv(env_var)
                if password:
                    return password
                logger.warning(
                    f"Environment variable {env_var} from secret_key_ref not set"
                )
            else:
                logger.warning(f"Unsupported secret_key_ref format: {secret_key_ref}")

        # Method 2: password_encrypted (decrypt using EncryptionManager)
        password_encrypted = conn_config.get("password_encrypted")
        if password_encrypted:
            try:
                manager = get_encryption_manager()
                return manager.decrypt(password_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt password: {e}")

        # Method 3: direct password (for testing/dev only)
        password = conn_config.get("password")
        if password:
            # BLOCKER-2: Block plaintext passwords in production
            is_production = os.getenv("ENV") in ("production", "prod")
            if is_production:
                raise ValueError(
                    "BLOCKER-2: Plaintext password not allowed in production. "
                    "Use secret_key_ref (env:VAR_NAME) or password_encrypted instead."
                )
            logger.warning(
                "Using direct password (not recommended for production). "
                "Migrate to secret_key_ref or password_encrypted."
            )
            return password

        raise ValueError(
            "Password not found in connection config. "
            "Ensure secret_key_ref, password_encrypted, or password is set."
        )


class PostgreSQLConnection(SourceConnection):
    """
    PostgreSQL/MySQL database connection.

    Supports PostgreSQL and MySQL using psycopg2/mysql-compatible drivers.
    """

    def connect(self) -> None:
        """Establish PostgreSQL connection."""
        try:
            import psycopg

            conn_config = self.source_asset.get("connection", {})
            self.connection = psycopg.connect(
                host=conn_config.get("host"),
                port=conn_config.get("port", 5432),
                user=conn_config.get("username"),
                password=self._resolve_password(),
                dbname=conn_config.get("database"),
                connect_timeout=conn_config.get("timeout", 30),
            )
            logger.info(
                f"Connected to PostgreSQL: {conn_config.get('host')}:{conn_config.get('port')}"
            )
        except ImportError:
            raise ImportError("psycopg library is required for PostgreSQL connections")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def execute(
        self, query: str, params: Dict[str, Any] | tuple | list | None = None
    ) -> Any:
        """Execute SQL query with template processing support."""
        if not self.connection:
            raise ConnectionError("Not connected to database")

        try:
            with self.connection.cursor() as cur:
                # Process SQL template if params is a dict with filters
                if isinstance(params, dict) and ("filters" in params or "where_clause" in query or "{where_clause}" in query or "{where}" in query):
                    processed_sql, processed_params = SQLTemplateProcessor.process_template(query, params)
                    execute_params = processed_params
                    query_to_execute = processed_sql
                elif params is None:
                    execute_params = ()
                    query_to_execute = query
                elif isinstance(params, dict):
                    # Check if query uses named placeholders (%(name)s)
                    if "%(" in query:
                        execute_params = params
                        query_to_execute = query
                    else:
                        # Convert dict to tuple for positional placeholders
                        execute_params = tuple(params.values())
                        query_to_execute = query
                elif isinstance(params, list):
                    execute_params = tuple(params)
                    query_to_execute = query
                else:
                    execute_params = params
                    query_to_execute = query

                # Validate parameter count if using positional placeholders
                if "%s" in query_to_execute and isinstance(execute_params, tuple):
                    if not SQLTemplateProcessor.validate_param_count(query_to_execute, execute_params):
                        logger.warning(
                            f"Parameter count mismatch for query. "
                            f"Placeholders: {SQLTemplateProcessor.extract_placeholder_count(query_to_execute)}, "
                            f"Params: {len(execute_params)}"
                        )

                cur.execute(query_to_execute, execute_params)
                # Check if this is a SELECT query
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    # For INSERT/UPDATE/DELETE, return rowcount
                    self.connection.commit()
                    return {"rowcount": cur.rowcount}
        except Exception as e:
            self.connection.rollback()
            raise RuntimeError(f"Query execution failed: {e}")

    def close(self) -> None:
        """Close PostgreSQL connection."""
        if self.connection:
            self.connection.close()
            self.connection = None


class Neo4jConnection(SourceConnection):
    """
    Neo4j graph database connection.

    Uses the official Neo4j Python driver.
    """

    def connect(self) -> None:
        """Establish Neo4j connection."""
        try:
            from neo4j import GraphDatabase

            conn_config = self.source_asset.get("connection", {})
            # Get URI from connection config
            uri = conn_config.get("uri")
            if not uri:
                # Fallback to building URI from host/port
                host = conn_config.get("host", "localhost")
                port = conn_config.get("port", "7687")
                uri = f"bolt://{host}:{port}"

            username = conn_config.get("username", "neo4j")
            password = self._resolve_password()
            database = conn_config.get("database", "neo4j")

            self.driver = GraphDatabase.driver(
                uri,
                auth=(username, password),
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j: {uri} (database: {database})")
        except ImportError:
            raise ImportError("neo4j library is required for Neo4j connections")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")

    def execute(self, query: str, params: Dict[str, Any] | None = None) -> Any:
        """Execute Cypher query."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            raise RuntimeError(f"Cypher execution failed: {e}")

    def close(self) -> None:
        """Close Neo4j connection."""
        if hasattr(self, "driver") and self.driver:
            self.driver.close()
            self.driver = None


class RestAPIConnection(SourceConnection):
    """
    REST API connection.

    Uses httpx for async HTTP requests to REST APIs.
    """

    def connect(self) -> None:
        """Initialize HTTP client."""
        try:
            import httpx

            conn_config = self.source_asset.get("connection", {})
            self.base_url = conn_config.get("host")
            self.client = httpx.Client(
                base_url=self.base_url,
                timeout=conn_config.get("timeout", 30),
            )
            logger.info(f"Initialized HTTP client for: {self.base_url}")
        except ImportError:
            raise ImportError("httpx library is required for REST API connections")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize HTTP client: {e}")

    def execute(self, query: Dict[str, Any], params: Dict[str, Any] | None = None) -> Any:
        """
        Execute HTTP request.

        Args:
            query: HTTP config dict with method, path, headers, etc.
            params: Optional parameters for URL substitution

        Returns:
            Parsed JSON response
        """
        if not self.client:
            raise ConnectionError("HTTP client not initialized")

        try:
            method = query.get("method", "GET").upper()
            path = query.get("path", "")
            headers = query.get("headers", {})
            body = query.get("body")

            # Substitute path parameters if provided
            if params:
                for key, value in params.items():
                    path = path.replace(f"{{{key}}}", str(value))

            response = self.client.request(
                method=method,
                url=path,
                headers=headers,
                json=body,
            )
            response.raise_for_status()

            # Apply response mapping if configured
            response_mapping = query.get("response_mapping", {})
            if response_mapping:
                return self._apply_mapping(response.json(), response_mapping)
            return response.json()

        except Exception as e:
            raise RuntimeError(f"HTTP request failed: {e}")

    def _apply_mapping(self, data: Any, mapping: Dict[str, str]) -> Any:
        """Apply JSONPath-based response mapping."""
        # Simple implementation - can be enhanced with JSONPath library
        items_path = mapping.get("items")
        if items_path and isinstance(data, dict):
            # Extract items from nested structure
            parts = items_path.split(".")
            for part in parts:
                data = data.get(part, data)
        return data

    def close(self) -> None:
        """Close HTTP client."""
        if hasattr(self, "client") and self.client:
            self.client.close()
            self.client = None


class ConnectionFactory:
    """
    Factory for creating source connections.

    Dynamically creates connections based on source type.
    """

    _creators: Dict[str, type[SourceConnection]] = {
        "postgres": PostgreSQLConnection,  # Legacy alias
        "postgresql": PostgreSQLConnection,
        "mysql": PostgreSQLConnection,  # Reuse PostgreSQL connection for MySQL
        "bigquery": PostgreSQLConnection,  # Can be specialized later
        "snowflake": PostgreSQLConnection,  # Can be specialized later
        "neo4j": Neo4jConnection,
        "rest_api": RestAPIConnection,
        "graphql_api": RestAPIConnection,  # Reuse REST API for GraphQL
    }

    @classmethod
    def create(cls, source_asset: Dict[str, Any]) -> SourceConnection:
        """
        Create a connection for the given source asset.

        Args:
            source_asset: Source asset dict with source_type and connection config

        Returns:
            SourceConnection instance appropriate for the source type

        Raises:
            ValueError: If source type is not supported
        """
        source_type = source_asset.get("source_type", "").lower()
        creator = cls._creators.get(source_type)

        if not creator:
            raise ValueError(
                f"Unsupported source type: {source_type}. "
                f"Supported types: {list(cls._creators.keys())}"
            )

        connection = creator(source_asset)
        connection.connect()
        return connection

    @classmethod
    def register_creator(
        cls, source_type: str, creator_class: type[SourceConnection]
    ) -> None:
        """
        Register a custom connection creator for a source type.

        Args:
            source_type: Source type identifier
            creator_class: SourceConnection subclass
        """
        cls._creators[source_type.lower()] = creator_class
        logger.info(f"Registered connection creator for: {source_type}")


def create_connection(source_asset: Dict[str, Any]) -> SourceConnection:
    """
    Convenience function for creating connections.

    Args:
        source_asset: Source asset dict with source_type and connection config

    Returns:
        Connected SourceConnection instance
    """
    return ConnectionFactory.create(source_asset)

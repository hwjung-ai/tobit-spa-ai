"""
Catalog Factory - Factory for creating database-specific catalog implementations.

This module provides a factory pattern for instantiating the appropriate
catalog class based on the source database type.
"""

from .base_catalog import BaseCatalog
from .postgres_catalog_new import PostgresCatalog
from .mysql_catalog import MySQLCatalog
from .oracle_catalog import OracleCatalog


class CatalogFactory:
    """Factory for creating appropriate catalog based on source type"""

    _registry: dict[str, type[BaseCatalog]] = {
        "postgresql": PostgresCatalog,
        "postgres": PostgresCatalog,
        "mysql": MySQLCatalog,
        "oracle": OracleCatalog,
        # "sqlserver": SQLServerCatalog,  # Coming soon
        # "neo4j": Neo4jCatalog,  # Coming soon
    }

    @classmethod
    def create(cls, source_asset: dict) -> BaseCatalog:
        """
        Create a catalog instance for the given source asset.

        Args:
            source_asset: Source Asset configuration dict

        Returns:
            Appropriate catalog instance

        Raises:
            ValueError: If source type is not supported
        """
        source_type = source_asset.get("source_type", "").lower()

        catalog_class = cls._registry.get(source_type)
        if not catalog_class:
            supported = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unsupported source type for schema discovery: {source_type}. "
                f"Supported types: {supported}"
            )

        return catalog_class(source_asset)

    @classmethod
    def register(cls, source_type: str, catalog_class: type[BaseCatalog]):
        """
        Register a custom catalog implementation.

        Args:
            source_type: Database type identifier (e.g., "postgresql", "mysql")
            catalog_class: Catalog class inheriting from BaseCatalog
        """
        cls._registry[source_type] = catalog_class

    @classmethod
    def supported_types(cls) -> list[str]:
        """Get list of supported source types"""
        return list(cls._registry.keys())

    @classmethod
    def is_supported(cls, source_type: str) -> bool:
        """Check if a source type is supported"""
        return source_type.lower() in cls._registry

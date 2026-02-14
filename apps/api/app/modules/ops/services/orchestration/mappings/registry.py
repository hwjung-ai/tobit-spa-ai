"""
Mapping registry implementation.

Provides centralized management of mapping assets with caching,
fallback support, and runtime reloading capabilities.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MappingRegistry:
    """
    Registry for managing mapping assets dynamically.

    Loads mappings from Asset Registry database with fallback to
    hardcoded defaults. Provides caching for performance.

    Dynamic mapping selection:
    - Stores multiple versions of each mapping (metric_aliases_v1, metric_aliases_v2, ...)
    - Tracks which version is "active" (set_active_mapping)
    - Returns active version when get_mapping is called
    """

    def __init__(self):
        """Initialize empty mapping registry with cache."""
        self._mappings: Dict[str, Any] = {}  # All loaded mappings
        self._cache: Dict[str, Any] = {}  # Cache for performance
        self._fallbacks: Dict[str, Any] = {}  # Default fallbacks
        self._active_mappings: Dict[str, str] = {}  # {"metric_aliases": "metric_aliases_v2"}

    def register_mapping(
        self,
        mapping_name: str,
        mapping_data: Any,
        source: str = "asset_registry",
    ) -> None:
        """
        Register a mapping with the registry.

        Args:
            mapping_name: Unique identifier for the mapping
            mapping_data: The mapping data structure
            source: Source of the mapping (asset_registry, fallback, etc)
        """
        self._mappings[mapping_name] = {
            "data": mapping_data,
            "source": source,
        }
        logger.info(f"Registered mapping: {mapping_name} (source={source})")

    def get_mapping(
        self, mapping_name: str, use_cache: bool = True
    ) -> Any:
        """
        Get a mapping by name.

        Args:
            mapping_name: Name of the mapping to retrieve
            use_cache: Whether to use cached value

        Returns:
            Mapping data structure

        Raises:
            ValueError: If mapping not found
        """
        # Check cache first
        if use_cache and mapping_name in self._cache:
            return self._cache[mapping_name]

        # Try to get from registry
        if mapping_name in self._mappings:
            data = self._mappings[mapping_name]["data"]
            self._cache[mapping_name] = data
            return data

        # Try fallback
        if mapping_name in self._fallbacks:
            logger.warning(f"Using fallback for mapping: {mapping_name}")
            data = self._fallbacks[mapping_name]
            self._cache[mapping_name] = data
            return data

        # Return empty dict instead of raising error (graceful fallback)
        logger.warning(f"Mapping not found, returning empty dict: {mapping_name}")
        return {}

    def register_fallback(
        self, mapping_name: str, fallback_data: Any
    ) -> None:
        """Register fallback data for a mapping."""
        self._fallbacks[mapping_name] = fallback_data
        logger.debug(f"Registered fallback for: {mapping_name}")

    def clear_cache(self, mapping_name: Optional[str] = None) -> None:
        """Clear cache for a specific mapping or all mappings."""
        if mapping_name:
            self._cache.pop(mapping_name, None)
        else:
            self._cache.clear()

    def list_mappings(self) -> List[str]:
        """List all registered mapping names."""
        return list(self._mappings.keys())

    def is_registered(self, mapping_name: str) -> bool:
        """Check if a mapping is registered."""
        return (
            mapping_name in self._mappings
            or mapping_name in self._fallbacks
        )

    def get_mapping_info(self, mapping_name: str) -> Dict[str, Any]:
        """Get metadata about a mapping."""
        if mapping_name in self._mappings:
            return {
                "name": mapping_name,
                "source": self._mappings[mapping_name]["source"],
                "cached": mapping_name in self._cache,
            }
        return {"name": mapping_name, "source": "not_found", "cached": False}

    def set_active_mapping(self, mapping_type: str, mapping_name: str) -> None:
        """
        Set which mapping version to use for a mapping type.

        Args:
            mapping_type: Type of mapping (e.g., "metric_aliases")
            mapping_name: Full name of mapping to activate (e.g., "metric_aliases_v2")

        Example:
            registry.set_active_mapping("metric_aliases", "metric_aliases_v2")
            # Now _get_metric_aliases() will use metric_aliases_v2
        """
        if mapping_name not in self._mappings and mapping_name not in self._fallbacks:
            raise ValueError(f"Mapping not found: {mapping_name}")

        self._active_mappings[mapping_type] = mapping_name
        # Clear cache for this type so new version is loaded
        self._cache.pop(mapping_type, None)
        logger.info(
            f"Activated mapping: {mapping_type} → {mapping_name}"
        )

    def get_active_mapping_name(self, mapping_type: str) -> str:
        """
        Get the name of the active mapping for a type.

        Args:
            mapping_type: Type of mapping (e.g., "metric_aliases")

        Returns:
            Active mapping name (e.g., "metric_aliases_v2")
        """
        # If explicitly set, use that
        if mapping_type in self._active_mappings:
            return self._active_mappings[mapping_type]

        # Otherwise use default (same name as type)
        return mapping_type

    def list_available_mappings(self, mapping_type: str) -> List[str]:
        """
        List all available versions of a mapping type.

        Args:
            mapping_type: Type of mapping (e.g., "metric_aliases")

        Returns:
            List of available mapping names
        """
        prefix = f"{mapping_type}"
        available = []

        # Check exact match
        if mapping_type in self._mappings or mapping_type in self._fallbacks:
            available.append(mapping_type)

        # Check versioned matches (metric_aliases_v1, metric_aliases_v2, ...)
        for name in list(self._mappings.keys()) + list(self._fallbacks.keys()):
            if name.startswith(f"{prefix}_v"):
                available.append(name)

        return available


# Global registry instance
_global_mapping_registry: Optional[MappingRegistry] = None


def get_mapping_registry() -> MappingRegistry:
    """Get the global mapping registry, creating it if necessary."""
    global _global_mapping_registry
    if _global_mapping_registry is None:
        _global_mapping_registry = MappingRegistry()
    return _global_mapping_registry


def get_mapping(mapping_name: str, use_cache: bool = True) -> Any:
    """
    Convenience function to get a mapping from the global registry.

    Args:
        mapping_name: Name of the mapping to retrieve
        use_cache: Whether to use cached value

    Returns:
        Mapping data structure
    """
    return get_mapping_registry().get_mapping(mapping_name, use_cache)

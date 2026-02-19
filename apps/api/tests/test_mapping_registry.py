"""Unit tests for mapping registry (DB-only, no fallback)."""

import pytest
from app.modules.ops.services.orchestration.mappings.registry import (
    MappingRegistry,
    get_mapping_registry,
)


def test_registry_initialization():
    registry = MappingRegistry()
    assert registry.list_mappings() == []


def test_register_and_retrieve_mapping():
    registry = MappingRegistry()
    test_data = {"keywords": ["test1", "test2"]}

    registry.register_mapping("test_mapping", test_data)
    result = registry.get_mapping("test_mapping")

    assert result == test_data


def test_cache_behavior():
    registry = MappingRegistry()
    test_data = {"keywords": ["cached"]}

    registry.register_mapping("cached_mapping", test_data)

    result1 = registry.get_mapping("cached_mapping")
    result2 = registry.get_mapping("cached_mapping")

    assert result1 == result2
    assert registry.get_mapping_info("cached_mapping")["cached"] is True


def test_missing_mapping_raises_error():
    registry = MappingRegistry()
    with pytest.raises(KeyError):
        registry.get_mapping("nonexistent_mapping")


def test_global_registry_singleton():
    reg1 = get_mapping_registry()
    reg2 = get_mapping_registry()
    assert reg1 is reg2


def test_clear_cache():
    registry = MappingRegistry()
    test_data = {"keywords": ["test"]}
    registry.register_mapping("test_mapping", test_data)

    registry.get_mapping("test_mapping")
    assert registry.get_mapping_info("test_mapping")["cached"] is True

    registry.clear_cache("test_mapping")
    assert registry.get_mapping_info("test_mapping")["cached"] is False


def test_list_mappings():
    registry = MappingRegistry()
    registry.register_mapping("mapping1", {})
    registry.register_mapping("mapping2", {})

    mappings = registry.list_mappings()
    assert "mapping1" in mappings
    assert "mapping2" in mappings


def test_is_registered():
    registry = MappingRegistry()
    registry.register_mapping("test_mapping", {})

    assert registry.is_registered("test_mapping") is True
    assert registry.is_registered("nonexistent") is False

"""Unit tests for mapping registry."""
import pytest

from app.modules.ops.services.ci.mappings.registry import (
    MappingRegistry,
    get_mapping_registry,
)
from app.modules.ops.services.ci.mappings.registry_init import (
    initialize_mappings,
)
from app.modules.ops.services.ci.mappings.compat import (
    _get_metric_aliases,
    _get_agg_keywords,
    _get_list_keywords,
    _get_filterable_fields,
)


@pytest.fixture(autouse=True)
def setup_registry():
    """Initialize registry before each test."""
    initialize_mappings()
    yield


def test_registry_initialization():
    """Test registry initializes correctly."""
    registry = MappingRegistry()
    assert registry.list_mappings() == []


def test_register_and_retrieve_mapping():
    """Test registering and retrieving a mapping."""
    registry = MappingRegistry()
    test_data = {"keywords": ["test1", "test2"]}

    registry.register_mapping("test_mapping", test_data)
    result = registry.get_mapping("test_mapping")

    assert result == test_data


def test_fallback_mechanism():
    """Test fallback is used when mapping not in registry."""
    registry = MappingRegistry()
    fallback_data = {"keywords": ["fallback"]}

    registry.register_fallback("missing_mapping", fallback_data)
    result = registry.get_mapping("missing_mapping")

    assert result == fallback_data


def test_cache_behavior():
    """Test caching works correctly."""
    registry = MappingRegistry()
    test_data = {"keywords": ["cached"]}

    registry.register_mapping("cached_mapping", test_data)

    # First call should cache
    result1 = registry.get_mapping("cached_mapping")
    # Second call should use cache
    result2 = registry.get_mapping("cached_mapping")

    assert result1 == result2
    assert registry.get_mapping_info("cached_mapping")["cached"] is True


def test_compat_metric_aliases():
    """Test backward compatibility for metric aliases."""
    aliases = _get_metric_aliases()
    assert "aliases" in aliases
    assert isinstance(aliases["aliases"], dict)
    assert "cpu" in aliases["aliases"]


def test_compat_agg_keywords():
    """Test backward compatibility for agg keywords."""
    agg = _get_agg_keywords()
    assert isinstance(agg, dict)
    assert "max" in agg.values() or len(agg) > 0


def test_compat_list_keywords():
    """Test backward compatibility for list keywords."""
    list_kw = _get_list_keywords()
    assert isinstance(list_kw, set)
    assert len(list_kw) > 0


def test_compat_filterable_fields():
    """Test backward compatibility for filterable fields (Bug #1 fix)."""
    fields = _get_filterable_fields()
    # Should have consistent key names
    assert "tag_filter_keys" in fields
    assert "attr_filter_keys" in fields
    assert isinstance(fields["tag_filter_keys"], set)
    assert isinstance(fields["attr_filter_keys"], set)


def test_missing_mapping_raises_error():
    """Test that missing mapping raises ValueError."""
    registry = MappingRegistry()
    with pytest.raises(ValueError):
        registry.get_mapping("nonexistent_mapping")


def test_global_registry_singleton():
    """Test that get_mapping_registry returns singleton."""
    reg1 = get_mapping_registry()
    reg2 = get_mapping_registry()
    assert reg1 is reg2


def test_clear_cache():
    """Test cache clearing functionality."""
    registry = MappingRegistry()
    test_data = {"keywords": ["test"]}
    registry.register_mapping("test_mapping", test_data)

    # Populate cache
    registry.get_mapping("test_mapping")
    assert registry.get_mapping_info("test_mapping")["cached"] is True

    # Clear cache
    registry.clear_cache("test_mapping")
    assert registry.get_mapping_info("test_mapping")["cached"] is False


def test_list_mappings():
    """Test listing all registered mappings."""
    registry = MappingRegistry()
    registry.register_mapping("mapping1", {})
    registry.register_mapping("mapping2", {})

    mappings = registry.list_mappings()
    assert "mapping1" in mappings
    assert "mapping2" in mappings


def test_is_registered():
    """Test checking if mapping is registered."""
    registry = MappingRegistry()
    registry.register_mapping("test_mapping", {})
    registry.register_fallback("fallback_mapping", {})

    assert registry.is_registered("test_mapping") is True
    assert registry.is_registered("fallback_mapping") is True
    assert registry.is_registered("nonexistent") is False

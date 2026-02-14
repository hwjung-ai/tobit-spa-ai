"""
CI Cache Performance Tests

Tests for the CICache implementation to verify:
- Cache hit/miss behavior
- TTL expiration
- LRU eviction
- Performance improvements
- Statistics tracking
"""

import asyncio
from datetime import timedelta

import pytest
from app.modules.ops.services.orchestration.services.ci_cache import CICache


class TestCICacheBasic:
    """Basic cache functionality tests"""

    @pytest.mark.asyncio
    async def test_cache_miss_on_empty_cache(self):
        """Test that empty cache returns None"""
        cache = CICache()
        key = "test_key"
        result = await cache.get(key)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test basic set and get operations"""
        cache = CICache()
        key = "test_key"
        test_data = [
            {"ci_id": "1", "ci_code": "DB01", "ci_type": "Database"},
            {"ci_id": "2", "ci_code": "APP02", "ci_type": "Application"},
        ]

        await cache.set(key, test_data, keywords=["db"], filters=None)
        result = await cache.get(key)

        assert result is not None
        assert len(result) == 2
        assert result[0]["ci_code"] == "DB01"

    @pytest.mark.asyncio
    async def test_cache_hit_tracking(self):
        """Test that cache hit count is incremented"""
        cache = CICache()
        key = "test_key"
        test_data = [{"ci_id": "1", "ci_code": "DB01"}]

        await cache.set(key, test_data)

        # First hit
        result1 = await cache.get(key)
        assert result1 is not None

        # Second hit
        result2 = await cache.get(key)
        assert result2 is not None

        stats = cache.get_stats()
        assert stats["hit_count"] == 2
        assert stats["miss_count"] == 0
        assert stats["hit_rate_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_cache_miss_tracking(self):
        """Test that cache miss count is incremented"""
        cache = CICache()

        # Miss on non-existent key
        await cache.get("nonexistent_key")

        stats = cache.get_stats()
        assert stats["miss_count"] == 1
        assert stats["hit_count"] == 0


class TestCICacheKeyGeneration:
    """Tests for cache key generation"""

    def test_key_generation_with_keywords_only(self):
        """Test cache key generation with keywords"""
        cache = CICache()

        key1 = cache.generate_key(keywords=["app01", "database"])
        key2 = cache.generate_key(keywords=["database", "app01"])  # Different order

        # Keys should be the same due to normalization
        assert key1 == key2

    def test_key_generation_with_filters(self):
        """Test cache key generation with filters"""
        cache = CICache()

        filters = [{"field": "ci_type", "value": "Database"}]
        key1 = cache.generate_key(keywords=["app"], filters=filters)
        key2 = cache.generate_key(keywords=["app"], filters=filters)

        assert key1 == key2

    def test_key_generation_with_limit_and_sort(self):
        """Test cache key includes limit and sort"""
        cache = CICache()

        key1 = cache.generate_key(
            keywords=["app"],
            limit=10,
            sort=("ci_code", "ASC"),
        )
        key2 = cache.generate_key(
            keywords=["app"],
            limit=20,
            sort=("ci_code", "ASC"),
        )

        assert key1 != key2

    def test_key_generation_normalizes_keywords(self):
        """Test that keywords are normalized"""
        cache = CICache()

        key1 = cache.generate_key(keywords=["APP01", "DATABASE"])
        key2 = cache.generate_key(keywords=["app01", "database"])

        assert key1 == key2


class TestCICacheExpiration:
    """Tests for TTL-based expiration"""

    @pytest.mark.asyncio
    async def test_keyword_ttl_override(self):
        """Test that keyword searches have longer TTL"""
        cache = CICache(
            default_ttl=timedelta(milliseconds=100),
            keyword_ttl=timedelta(seconds=10),  # Much longer
        )
        key = "test_key"
        test_data = [{"ci_id": "1"}]

        # Set with keywords (should use keyword_ttl)
        await cache.set(key, test_data, keywords=["app"], filters=None)

        # Wait a bit
        await asyncio.sleep(0.15)

        # Should still exist due to longer TTL
        result = await cache.get(key)
        assert result is not None

    @pytest.mark.asyncio
    async def test_filter_ttl_override(self):
        """Test that filter searches have configurable TTL"""
        cache = CICache(
            default_ttl=timedelta(milliseconds=100),
            filter_ttl=timedelta(milliseconds=100),
        )
        key = "test_key"
        test_data = [{"ci_id": "1"}]

        # Set with filters
        filters = [{"field": "type", "value": "app"}]
        await cache.set(key, test_data, keywords=None, filters=filters)

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        result = await cache.get(key)
        assert result is None


class TestCICacheLRUEviction:
    """Tests for LRU eviction policy"""

    @pytest.mark.asyncio
    async def test_lru_eviction_on_max_size(self):
        """Test that least recently used entries are evicted"""
        cache = CICache(max_size=3, default_ttl=timedelta(seconds=300))

        # Add 3 entries
        for i in range(3):
            key = f"key_{i}"
            data = [{"ci_id": str(i)}]
            await cache.set(key, data)

        # Access first two keys to make third key least recently used
        await cache.get("key_0")
        await cache.get("key_1")

        # Add 4th entry - should evict key_2
        await cache.set("key_3", [{"ci_id": "3"}])

        stats = cache.get_stats()
        assert stats["cache_size"] == 3
        assert stats["eviction_count"] == 1

        # key_2 should be gone
        result = await cache.get("key_2")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction_respects_access_pattern(self):
        """Test that frequently accessed entries are kept"""
        cache = CICache(max_size=2, default_ttl=timedelta(seconds=300))

        # Add 2 entries
        await cache.set("key_1", [{"ci_id": "1"}])
        await cache.set("key_2", [{"ci_id": "2"}])

        # Access key_1 multiple times
        for _ in range(5):
            await cache.get("key_1")

        # Add 3rd entry - should evict key_2 (less accessed)
        await cache.set("key_3", [{"ci_id": "3"}])

        # key_1 should still exist
        result1 = await cache.get("key_1")
        assert result1 is not None

        # key_2 should be evicted
        result2 = await cache.get("key_2")
        assert result2 is None


class TestCICacheInvalidation:
    """Tests for cache invalidation"""

    @pytest.mark.asyncio
    async def test_invalidate_single_entry(self):
        """Test invalidating a single cache entry"""
        cache = CICache()
        key = "test_key"
        test_data = [{"ci_id": "1"}]

        await cache.set(key, test_data)
        assert await cache.contains(key)

        # Invalidate
        success = await cache.invalidate(key)
        assert success is True
        assert not await cache.contains(key)

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_entry(self):
        """Test that invalidating non-existent entry returns False"""
        cache = CICache()
        success = await cache.invalidate("nonexistent_key")
        assert success is False

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self):
        """Test pattern-based invalidation"""
        cache = CICache()

        # Add entries with different keywords
        await cache.set("key_1", [{"ci_id": "1"}], keywords=["database"])
        await cache.set("key_2", [{"ci_id": "2"}], keywords=["application"])
        await cache.set("key_3", [{"ci_id": "3"}], keywords=["database", "mysql"])

        # Invalidate all entries matching "database"
        count = await cache.invalidate_pattern(["database"])
        assert count == 2

        # Verify invalidation
        assert await cache.contains("key_1") is False
        assert await cache.contains("key_2") is True
        assert await cache.contains("key_3") is False

    @pytest.mark.asyncio
    async def test_clear_all(self):
        """Test clearing all cache entries"""
        cache = CICache()

        # Add multiple entries
        for i in range(5):
            await cache.set(f"key_{i}", [{"ci_id": str(i)}])

        stats_before = cache.get_stats()
        assert stats_before["cache_size"] == 5

        # Clear all
        await cache.clear()

        stats_after = cache.get_stats()
        assert stats_after["cache_size"] == 0


class TestCICacheStatistics:
    """Tests for cache statistics"""

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        """Test that hit rate is calculated correctly"""
        cache = CICache()
        key = "test_key"
        test_data = [{"ci_id": "1"}]

        await cache.set(key, test_data)

        # Generate hits and misses
        await cache.get(key)  # hit
        await cache.get(key)  # hit
        await cache.get("missing_key")  # miss
        await cache.get(key)  # hit

        stats = cache.get_stats()
        assert stats["hit_count"] == 3
        assert stats["miss_count"] == 1
        assert stats["total_requests"] == 4
        assert stats["hit_rate_percent"] == 75.0

    @pytest.mark.asyncio
    async def test_get_entries_summary(self):
        """Test that entries summary is generated correctly"""
        cache = CICache()

        await cache.set("key_1", [{"ci_id": "1"}], keywords=["app", "server"])
        await cache.set("key_2", [{"ci_id": "2", "ci_id": "3"}], keywords=["db"])

        # Access to update last_accessed
        await cache.get("key_1")

        entries = cache.get_entries_summary()

        assert len(entries) == 2
        assert entries[0]["key"] == "key_1"[:8]
        assert entries[0]["results"] == 1
        assert entries[0]["hit_count"] >= 1
        assert "app" in entries[0]["query_keywords"]


class TestCICachePerformance:
    """Performance and concurrent access tests"""

    @pytest.mark.asyncio
    async def test_concurrent_reads(self):
        """Test concurrent read operations"""
        cache = CICache()
        key = "test_key"
        test_data = [{"ci_id": f"{i}"} for i in range(100)]

        await cache.set(key, test_data)

        # Concurrent reads
        tasks = [cache.get(key) for _ in range(100)]
        results = await asyncio.gather(*tasks)

        assert all(result is not None for result in results)
        assert len(results) == 100

    @pytest.mark.asyncio
    async def test_concurrent_writes(self):
        """Test concurrent write operations"""
        cache = CICache(max_size=1000)

        # Concurrent writes
        tasks = [
            cache.set(f"key_{i}", [{"ci_id": str(i)}])
            for i in range(100)
        ]
        await asyncio.gather(*tasks)

        stats = cache.get_stats()
        assert stats["cache_size"] == 100

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self):
        """Test mixed read/write operations"""
        cache = CICache(max_size=200)

        # Initial populate
        for i in range(50):
            await cache.set(f"key_{i}", [{"ci_id": str(i)}])

        # Mixed operations
        async def mixed_ops():
            tasks = []
            for i in range(25):
                tasks.append(cache.get(f"key_{i}"))
                tasks.append(cache.set(f"key_{i+50}", [{"ci_id": str(i+50)}]))
            await asyncio.gather(*tasks)

        await mixed_ops()

        stats = cache.get_stats()
        assert stats["cache_size"] > 0
        assert stats["hit_count"] > 0


class TestCICacheIntegration:
    """Integration tests with realistic scenarios"""

    @pytest.mark.asyncio
    async def test_repeated_search_pattern(self):
        """Test repeated CI searches (common pattern)"""
        cache = CICache()

        # Simulate repeated searches for same keywords
        keywords = ["database", "mysql"]
        filters = None

        search_results = [
            {"ci_id": f"db_{i}", "ci_code": f"MYSQL_{i}", "ci_type": "Database"}
            for i in range(10)
        ]

        cache_key = cache.generate_key(keywords=keywords, filters=filters)

        # First search - cache miss
        result1 = await cache.get(cache_key)
        assert result1 is None

        # Set cache
        await cache.set(cache_key, search_results, keywords=keywords, filters=filters)

        # Repeated searches - cache hits
        for _ in range(5):
            result = await cache.get(cache_key)
            assert result is not None
            assert len(result) == 10

        stats = cache.get_stats()
        assert stats["hit_count"] == 5
        assert stats["miss_count"] == 1

    @pytest.mark.asyncio
    async def test_related_ci_lookups(self):
        """Test related CI detail lookups (graph traversal)"""
        cache = CICache()

        ci_details = {
            "app_001": {"ci_id": "app_001", "ci_code": "APP_001", "ci_type": "Application"},
            "db_001": {"ci_id": "db_001", "ci_code": "DB_001", "ci_type": "Database"},
            "cache_001": {"ci_id": "cache_001", "ci_code": "CACHE_001", "ci_type": "Cache"},
        }

        # Simulate graph traversal - looking up related CIs
        for ci_id, detail in ci_details.items():
            cache_key = f"ci.get:{ci_id}"
            await cache.set(cache_key, [detail], keywords=[ci_id])

        # Access pattern: traverse graph and revisit CIs
        # First access of each: miss, subsequent accesses: hit
        for ci_id in ["app_001", "db_001", "cache_001", "app_001", "db_001"]:
            cache_key = f"ci.get:{ci_id}"
            result = await cache.get(cache_key)
            assert result is not None

        stats = cache.get_stats()
        # 5 gets: first 3 are cache hits (they were set), last 2 are also hits
        # Total: 5 hits (all cached entries exist)
        assert stats["hit_count"] == 5
        assert stats["miss_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

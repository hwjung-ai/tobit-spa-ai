# CI Cache Implementation Guide

**Document Type**: Developer Guide
**Date**: 2026-02-06
**Component**: OPS Module - CI Search Optimization

---

## Overview

This guide explains how to implement and extend the CI cache system for performance optimization. The CI cache reduces database queries by caching search results and CI details with intelligent TTL-based expiration.

---

## Architecture

### Component Structure

```
ops/
├── services/
│   └── ci/
│       ├── services/
│       │   ├── __init__.py
│       │   └── ci_cache.py          ← Cache implementation
│       └── orchestrator/
│           └── runner.py             ← Integration point
```

### Data Flow

```
Request (search/get)
    ↓
Check Cache (CICache.get)
    ↓
Cache Hit? ──YES→ Return cached result
    ↓ NO
Database Query
    ↓
Cache Result (CICache.set)
    ↓
Return Result
```

---

## Cache Design

### Key Components

#### 1. CICacheEntry (Data Model)

```python
@dataclass
class CICacheEntry:
    key: str                          # Cache key
    results: List[Dict[str, Any]]     # Cached results
    created_at: datetime              # Creation timestamp
    expires_at: datetime              # Expiration timestamp
    hit_count: int = 0                # Number of cache hits
    query_keywords: List[str] = []    # Original keywords
    filter_count: int = 0             # Number of filters
    result_count: int = 0             # Number of results
    last_accessed: datetime           # Last access time
```

#### 2. CICache (Main Class)

```python
class CICache:
    # Core Operations
    async def get(key: str) -> Optional[List[Dict]]
    async def set(key: str, results: List[Dict], ...) -> None
    async def invalidate(key: str) -> bool
    async def invalidate_pattern(keywords: Sequence) -> int
    async def clear() -> None
    async def contains(key: str) -> bool

    # Utilities
    def generate_key(...) -> str
    def get_stats() -> Dict
    def get_entries_summary() -> List[Dict]
```

### Key Generation Algorithm

```python
def generate_key(
    keywords: Sequence[str] | None = None,
    filters: Sequence[Dict] | None = None,
    limit: int | None = None,
    sort: Tuple[str, str] | None = None,
) -> str:
    """
    Steps:
    1. Normalize keywords: lowercase, trim, deduplicate
    2. Sort keywords alphabetically
    3. Serialize filters in deterministic order
    4. Include limit and sort parameters
    5. Create JSON payload
    6. Return MD5 hash
    """
```

---

## Integration Steps

### Step 1: Import CICache

```python
from app.modules.ops.services.ci.services.ci_cache import CICache
from datetime import timedelta
```

### Step 2: Initialize Cache in Constructor

```python
def __init__(self, ...):
    # ... existing initialization ...

    # CI search cache for performance optimization
    self._ci_search_cache = CICache(
        max_size=500,
        default_ttl=timedelta(seconds=300),
    )
```

### Step 3: Integrate in Search Methods

**Before**:
```python
async def _ci_search_async(self, keywords, filters, limit, sort):
    # Direct database call
    result_data = await self._ci_search_via_registry_async(
        keywords=keywords,
        filters=filters,
        limit=limit,
        sort=sort,
    )
    return result_data
```

**After**:
```python
async def _ci_search_async(self, keywords, filters, limit, sort):
    # Generate cache key
    cache_key = self._ci_search_cache.generate_key(
        keywords=keywords,
        filters=filters,
        limit=limit,
        sort=sort,
    )

    # Check cache first
    cached_results = await self._ci_search_cache.get(cache_key)
    if cached_results is not None:
        return cached_results

    # Cache miss - query database
    result_data = await self._ci_search_via_registry_async(...)

    # Store in cache
    if result_data:
        await self._ci_search_cache.set(
            cache_key,
            result_data,
            keywords=keywords,
            filters=filters,
        )

    return result_data
```

### Step 4: Similar Integration for Get Methods

```python
async def _ci_get_async(self, ci_id: str):
    # Check cache
    cache_key = f"ci.get:{ci_id}"
    cached = await self._ci_search_cache.get(cache_key)
    if cached is not None:
        return cached[0] if isinstance(cached, list) else cached

    # Query database
    detail = await self._ci_get_via_registry_async(ci_id)

    # Cache result
    if detail:
        await self._ci_search_cache.set(
            cache_key,
            [detail],
            keywords=[ci_id],
        )

    return detail
```

---

## Usage Examples

### Basic Usage

```python
# Initialize cache
cache = CICache(max_size=500, default_ttl=timedelta(minutes=5))

# Generate key
key = cache.generate_key(
    keywords=["database", "mysql"],
    filters=[{"field": "type", "value": "Database"}],
    limit=10
)

# Check cache
results = await cache.get(key)
if results is None:
    # Cache miss - query database
    results = fetch_from_db()
    # Store in cache
    await cache.set(key, results, keywords=["database"], filters=[...])

# Use results
for result in results:
    process(result)
```

### Advanced Usage

```python
# Get cache statistics
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate_percent']}%")
print(f"Size: {stats['cache_size']}/{stats['max_size']}")

# Invalidate specific entry
await cache.invalidate(key)

# Invalidate by pattern
count = await cache.invalidate_pattern(["database"])
print(f"Invalidated {count} entries")

# Clear entire cache
await cache.clear()

# Get entry details
entries = cache.get_entries_summary()
for entry in entries:
    print(f"{entry['key']}: {entry['results']} results")
```

---

## Configuration

### Default Settings

```python
CICache(
    max_size=500,                              # Cache entries
    default_ttl=timedelta(seconds=300),        # 5 minutes
    keyword_ttl=timedelta(seconds=600),        # 10 minutes
    filter_ttl=timedelta(seconds=300),         # 5 minutes
)
```

### Common Configurations

**High-Traffic Web Application**:
```python
CICache(
    max_size=1000,
    default_ttl=timedelta(seconds=600),
    keyword_ttl=timedelta(seconds=1200),
)
```

**Data Analysis Pipeline**:
```python
CICache(
    max_size=200,
    default_ttl=timedelta(seconds=180),
    keyword_ttl=timedelta(seconds=300),
)
```

**Real-Time System**:
```python
CICache(
    max_size=500,
    default_ttl=timedelta(seconds=120),
    keyword_ttl=timedelta(seconds=180),
)
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| get() | O(1) | Hash map lookup |
| set() | O(n log n) if eviction | LRU search for eviction |
| generate_key() | O(k + f log f) | k=keywords, f=filters |
| invalidate_pattern() | O(n) | n=cache size |

### Space Complexity

- Per entry: ~1-2KB (typical result)
- Total: max_size × average_entry_size
- Example: 500 entries × 2KB = 1MB

### Latency

- Cache hit: 1-5ms
- Cache miss: 50-100ms (DB dependent)
- Average operation: 30-50ms (with 80% hit rate)

---

## Monitoring & Debugging

### Enabling Debug Logging

```python
# Cache includes debug logging
logger.debug("ci_cache.hit", extra={...})
logger.debug("ci_cache.set", extra={...})
logger.debug("ci_cache.evict_lru", extra={...})
logger.info("ci_cache.invalidate_pattern", extra={...})
```

### Statistics Tracking

```python
# Get cache health metrics
stats = cache.get_stats()

# Metrics provided:
{
    'hit_count': int,           # Total cache hits
    'miss_count': int,          # Total cache misses
    'hit_rate_percent': float,  # Hit rate percentage
    'total_requests': int,      # Total requests
    'cache_size': int,          # Current entries
    'max_size': int,            # Maximum entries
    'eviction_count': int,      # LRU evictions
    'default_ttl_seconds': float,
    'keyword_ttl_seconds': float,
    'filter_ttl_seconds': float,
}
```

### Entry Summary

```python
# Get detailed entry information
entries = cache.get_entries_summary()

# Each entry includes:
{
    'key': str,              # Cache key (first 8 chars)
    'results': int,          # Number of cached results
    'age_seconds': int,      # Age of entry
    'expires_in_seconds': int,  # Time until expiration
    'hit_count': int,        # Hits for this entry
    'filter_count': int,     # Number of filters
    'query_keywords': list,  # Original keywords
}
```

---

## Thread Safety

### Concurrency

```python
# All operations are thread-safe
# Uses asyncio.Lock for synchronization

# Safe for concurrent reads
tasks = [cache.get(key) for _ in range(100)]
results = await asyncio.gather(*tasks)

# Safe for concurrent writes
tasks = [cache.set(f"key_{i}", [...]) for i in range(100)]
await asyncio.gather(*tasks)

# Safe for mixed operations
await asyncio.gather(
    cache.get("key1"),
    cache.set("key2", [...]),
    cache.invalidate("key3"),
)
```

---

## Testing

### Unit Tests

```python
# Test cache operations
async def test_cache_hit():
    cache = CICache()
    await cache.set("key", [{"id": 1}])
    result = await cache.get("key")
    assert result == [{"id": 1}]

# Test key generation
def test_key_normalization():
    cache = CICache()
    key1 = cache.generate_key(keywords=["APP", "Database"])
    key2 = cache.generate_key(keywords=["database", "app"])
    assert key1 == key2  # Normalized

# Test statistics
async def test_hit_rate():
    cache = CICache()
    await cache.set("key", [...])
    await cache.get("key")  # hit
    await cache.get("key")  # hit
    await cache.get("missing")  # miss

    stats = cache.get_stats()
    assert stats["hit_rate_percent"] == 66.67
```

### Integration Tests

See `/apps/api/tests/test_ci_cache_performance.py` for comprehensive examples.

---

## Troubleshooting

### Low Cache Hit Rate

**Symptoms**: Hit rate < 50%

**Causes**:
1. Keywords changing frequently
2. Filters with temporal conditions (timestamps)
3. Cache size too small
4. TTL too short

**Solutions**:
```python
# Increase cache size
CICache(max_size=1000)

# Increase TTL
CICache(default_ttl=timedelta(minutes=10))

# Check for temporal filters
if has_timestamp_filter(filters):
    # Use shorter TTL
    cache.set(key, data, ...)
```

### High Memory Usage

**Symptoms**: Memory growing beyond expected

**Causes**:
1. Cache size set too high
2. Large result sets
3. Memory leak in entry objects

**Solutions**:
```python
# Reduce cache size
CICache(max_size=250)

# Monitor memory
stats = cache.get_stats()
total_memory = stats['cache_size'] * average_entry_size

# Clear cache periodically
await cache.clear()
```

### Stale Data in Cache

**Symptoms**: Users see outdated CI information

**Causes**:
1. TTL too long
2. Database updated without cache invalidation
3. No cache invalidation on data changes

**Solutions**:
```python
# Invalidate on database updates
async def update_ci(ci_id, new_data):
    # Update database
    await db.update(ci_id, new_data)

    # Invalidate cache
    await cache.invalidate(f"ci.get:{ci_id}")

    # Or invalidate pattern
    await cache.invalidate_pattern([ci_id])

# Reduce TTL for frequently changing data
CICache(default_ttl=timedelta(minutes=1))
```

---

## Best Practices

### 1. Key Generation

✅ **DO**:
```python
# Include all parameters that affect results
key = cache.generate_key(
    keywords=keywords,
    filters=filters,
    limit=limit,
    sort=sort
)
```

❌ **DON'T**:
```python
# Don't ignore parameters
key = cache.generate_key(keywords=keywords)  # Missing filters!
```

### 2. TTL Selection

✅ **DO**:
```python
# Different TTL for different query types
if has_filter(filters):
    ttl = timedelta(minutes=5)  # Shorter for filters
else:
    ttl = timedelta(minutes=10)  # Longer for keywords
```

❌ **DON'T**:
```python
# One TTL for all
cache.set(key, data)  # Uses default, may not be optimal
```

### 3. Cache Invalidation

✅ **DO**:
```python
# Invalidate on updates
async def update_ci(ci_id, data):
    await db.update(ci_id, data)
    await cache.invalidate(f"ci.get:{ci_id}")
    await cache.invalidate_pattern([ci_id])
```

❌ **DON'T**:
```python
# Forget to invalidate
async def update_ci(ci_id, data):
    await db.update(ci_id, data)
    # Cache still has old data!
```

### 4. Monitoring

✅ **DO**:
```python
# Monitor cache health
stats = cache.get_stats()
if stats['hit_rate_percent'] < 50:
    logger.warning("Low cache hit rate")
```

❌ **DON'T**:
```python
# Ignore cache statistics
# Can't identify performance issues
```

---

## Future Enhancements

### Planned Features

1. **Cache Warming**
   - Pre-load common searches on startup
   - Periodic refresh of popular entries

2. **Redis Backend**
   - Distributed cache for multi-process deployments
   - Persistent cache across restarts

3. **Cache Partitioning**
   - Separate caches by tenant
   - Tenant-specific TTL policies

4. **Smart Invalidation**
   - Automatic invalidation on related updates
   - Dependency tracking

5. **Analytics**
   - Detailed cache performance metrics
   - Per-endpoint cache statistics

---

## Related Documentation

- [OPS Performance Optimization Report](./OPS_PERFORMANCE_OPTIMIZATION.md)
- [Runner Integration Guide](./CI_ORCHESTRATOR_RUNNER.md)
- [Test Coverage Report](../apps/api/tests/test_ci_cache_performance.py)

---

## Questions & Support

For implementation questions or issues:

1. Check the troubleshooting section above
2. Review test examples in `test_ci_cache_performance.py`
3. Examine usage in `runner.py`
4. Refer to inline documentation in `ci_cache.py`


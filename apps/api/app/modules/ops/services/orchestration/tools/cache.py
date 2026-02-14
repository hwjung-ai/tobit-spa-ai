from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    key: str
    value: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    miss_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


class ToolResultCache:
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: timedelta = timedelta(minutes=5),
        ttl_overrides: Optional[Dict[str, Dict[str, timedelta]]] = None,
    ):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._ttl_overrides = ttl_overrides or {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            if datetime.now() >= entry.expires_at:
                del self._cache[key]
                return None
            entry.hit_count += 1
            entry.last_accessed = datetime.now()
            return entry.value

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[timedelta] = None,
        tool_type: str | None = None,
        operation: str | None = None,
    ):
        async with self._lock:
            if len(self._cache) >= self._max_size:
                # Evict least recently used entry
                lru_key = min(
                    self._cache.values(), key=lambda entry: entry.last_accessed
                ).key
                del self._cache[lru_key]

            ttl_value = ttl or self._determine_ttl(tool_type, operation)
            now = datetime.now()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl_value,
            )
            self._cache[key] = entry

    def generate_key(
        self, tool_type: str, operation: str, params: Dict[str, Any]
    ) -> str:
        cacheable_params = {
            k: v
            for k, v in params.items()
            if k not in {"operation", "request_id", "trace_id"}
        }
        key_payload = json.dumps(
            {"tool": tool_type, "operation": operation, "params": cacheable_params},
            sort_keys=True,
            default=str,
        )
        return hashlib.md5(key_payload.encode()).hexdigest()

    def _determine_ttl(self, tool_type: str | None, operation: str | None) -> timedelta:
        if tool_type and operation:
            overrides = self._ttl_overrides.get(tool_type.upper())
            if overrides:
                override = overrides.get(operation)
                if override:
                    return override
        return self._default_ttl

    async def contains(self, key: str) -> bool:
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return False
            if datetime.now() >= entry.expires_at:
                del self._cache[key]
                return False
            return True

    def snapshot_keys(self) -> Dict[str, bool]:
        now = datetime.now()
        return {key: (entry.expires_at > now) for key, entry in self._cache.items()}

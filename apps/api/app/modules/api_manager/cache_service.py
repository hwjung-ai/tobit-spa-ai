from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheItem:
    value: dict[str, Any]
    expires_at: float


class APICacheService:
    """
    Lightweight in-memory API result cache.
    Used as a safe default for CEP-triggered API actions.
    """

    def __init__(self):
        self._items: dict[str, _CacheItem] = {}

    def _make_key(self, api_id: str, params: dict[str, Any]) -> str:
        payload = json.dumps(params or {}, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"api:{api_id}:{digest}"

    def get(self, api_id: str, params: dict[str, Any]) -> dict[str, Any] | None:
        key = self._make_key(api_id, params)
        item = self._items.get(key)
        if not item:
            return None
        if item.expires_at < time.time():
            self._items.pop(key, None)
            return None
        return item.value

    def set(
        self,
        api_id: str,
        params: dict[str, Any],
        value: dict[str, Any],
        ttl_seconds: int = 300,
    ) -> None:
        key = self._make_key(api_id, params)
        self._items[key] = _CacheItem(
            value=value,
            expires_at=time.time() + max(1, ttl_seconds),
        )

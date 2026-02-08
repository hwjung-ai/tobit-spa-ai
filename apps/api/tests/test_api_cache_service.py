from __future__ import annotations

from app.modules.api_manager.cache_service import APICacheService


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self.last_ttl: int | None = None

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> bool:
        self.last_ttl = ttl
        self._store[key] = value
        return True


class _BrokenRedis:
    def ping(self) -> bool:
        return True

    def get(self, _key: str) -> str | None:
        raise RuntimeError("redis read failed")

    def setex(self, _key: str, _ttl: int, _value: str) -> bool:
        raise RuntimeError("redis write failed")


def test_memory_cache_round_trip() -> None:
    svc = APICacheService(use_redis=False)
    payload = {"rows": [{"id": 1}], "status": "ok"}

    assert svc.get("api-1", {"tenant_id": "t1"}) is None
    svc.set("api-1", {"tenant_id": "t1"}, payload, ttl_seconds=60)
    assert svc.get("api-1", {"tenant_id": "t1"}) == payload

    stats = svc.get_stats()
    assert stats["backend"] == "memory"
    assert stats["hit_count"] == 1
    assert stats["miss_count"] == 1


def test_redis_cache_round_trip() -> None:
    redis = _FakeRedis()
    svc = APICacheService(use_redis=True, redis_client=redis)
    payload = {"value": 42}

    svc.set("api-2", {"q": "cpu"}, payload, ttl_seconds=120)
    cached = svc.get("api-2", {"q": "cpu"})

    assert cached == payload
    assert redis.last_ttl == 120
    assert svc.backend == "redis"


def test_redis_failure_falls_back_to_memory() -> None:
    svc = APICacheService(use_redis=True, redis_client=_BrokenRedis())
    payload = {"fallback": True}

    svc.set("api-3", {"k": "v"}, payload, ttl_seconds=30)
    cached = svc.get("api-3", {"k": "v"})

    assert cached == payload
    assert svc.backend == "memory"

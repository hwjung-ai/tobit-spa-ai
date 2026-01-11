from __future__ import annotations

from typing import Any

from redis import Redis

from core.config import AppSettings
from core.redis import create_redis_client


def get_client(settings: AppSettings) -> Redis:
    return create_redis_client(settings)


def scan_keys(
    client: Redis,
    pattern: str,
    cursor: int,
    count: int,
) -> tuple[int, list[str]]:
    next_cursor, keys = client.scan(cursor=cursor, match=pattern, count=count)
    return int(next_cursor), list(keys)


def get_key_value(client: Redis, key: str, value_type: str, limit: int) -> Any:
    if value_type == "string":
        return client.get(key)
    if value_type == "hash":
        return client.hscan(key, count=limit)[1]
    if value_type == "list":
        return client.lrange(key, 0, limit - 1)
    if value_type == "set":
        items = []
        for item in client.sscan_iter(key, count=limit):
            items.append(item)
            if len(items) >= limit:
                break
        return items
    if value_type == "zset":
        return client.zrange(key, 0, limit - 1, withscores=True)
    if value_type == "stream":
        return client.xrange(key, count=limit)
    return None

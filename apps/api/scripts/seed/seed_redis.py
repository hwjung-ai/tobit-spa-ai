from __future__ import annotations

import os
from pathlib import Path

import redis

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def load_env():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=_ENV_PATH)


def env_value(key: str, default: str | None = None) -> str:
    value = os.environ.get(key)
    if not value and default is None:
        raise RuntimeError(f"Missing environment variable {key}")
    return value or default  # type: ignore[return-value]


def seed():
    load_env()
    url = env_value("REDIS_URL")
    client = redis.Redis.from_url(url, decode_responses=True)
    namespace = env_value("DATA_REDIS_ALLOWED_PREFIXES", "cep:")
    sample_keys = [
        f"{namespace}notification:latest",
        f"{namespace}metric:cpu:1",
        f"{namespace}config:node",
    ]
    client.set(sample_keys[0], "unacked")
    client.hset(sample_keys[1], mapping={"value": "72", "unit": "%"})
    client.hset(sample_keys[2], mapping={"owner": "ops", "status": "active"})
    client.lpush(f"{namespace}history", "event1", "event2", "event3")
    print("Redis seed complete. Keys set:", ", ".join(sample_keys))


if __name__ == "__main__":
    seed()

from __future__ import annotations

import shlex
from typing import Any

from core.config import AppSettings

from app.modules.data_explorer.repositories import redis_repo

_ALLOWED_COMMANDS = {
    "get",
    "mget",
    "hget",
    "hgetall",
    "hscan",
    "lrange",
    "zrange",
    "zrevrange",
    "sscan",
    "scan",
    "type",
    "ttl",
    "exists",
    "xlen",
    "xrange",
    "xrevrange",
}


def scan(
    settings: AppSettings,
    prefix: str,
    pattern: str,
    cursor: int,
    count: int,
) -> dict[str, Any]:
    _validate_prefix(prefix, settings)
    pattern_value = pattern or f"{prefix}*"
    if not pattern_value.startswith(prefix):
        raise ValueError("Pattern must start with allowed prefix")
    client = redis_repo.get_client(settings)
    next_cursor, keys = redis_repo.scan_keys(client, pattern_value, cursor, count)
    return {"cursor": next_cursor, "keys": keys}


def get_key(settings: AppSettings, key: str) -> dict[str, Any]:
    _validate_key(key, settings)
    client = redis_repo.get_client(settings)
    value_type = client.type(key)
    ttl = client.ttl(key)
    value = redis_repo.get_key_value(client, key, value_type, settings.data_max_rows)
    return {"key": key, "type": value_type, "ttl": ttl, "value": value}


def run_command(settings: AppSettings, command: str) -> Any:
    tokens = shlex.split(command)
    if not tokens:
        raise ValueError("Command is empty")
    cmd = tokens[0].lower()
    if cmd not in _ALLOWED_COMMANDS:
        raise ValueError("Command is not allowed")
    _validate_command_keys(tokens, settings)
    client = redis_repo.get_client(settings)
    return _execute_command(client, cmd, tokens[1:], settings.data_max_rows)


def _validate_prefix(prefix: str, settings: AppSettings) -> None:
    allowed = _allowed_prefixes(settings)
    if not any(prefix.startswith(item) for item in allowed):
        raise ValueError("Prefix is not allowed")


def _validate_key(key: str, settings: AppSettings) -> None:
    allowed = _allowed_prefixes(settings)
    if not any(key.startswith(item) for item in allowed):
        raise ValueError("Key is not allowed")


def _allowed_prefixes(settings: AppSettings) -> list[str]:
    return [item.strip() for item in settings.data_redis_allowed_prefixes.split(",") if item.strip()]


def _validate_command_keys(tokens: list[str], settings: AppSettings) -> None:
    cmd = tokens[0].lower()
    if cmd in {"scan"}:
        _validate_scan_pattern(tokens, settings)
        return
    if cmd in {"mget"}:
        keys = tokens[1:]
    else:
        keys = tokens[1:2]
    for key in keys:
        if key.startswith("-"):
            continue
        _validate_key(key, settings)


def _validate_scan_pattern(tokens: list[str], settings: AppSettings) -> None:
    allowed = _allowed_prefixes(settings)
    lowered = [token.lower() for token in tokens]
    if "match" not in lowered:
        raise ValueError("SCAN requires MATCH with allowed prefix")
    match_index = lowered.index("match")
    if len(tokens) <= match_index + 1:
        raise ValueError("SCAN MATCH pattern is missing")
    pattern = tokens[match_index + 1]
    if not any(pattern.startswith(prefix) for prefix in allowed):
        raise ValueError("SCAN pattern must start with allowed prefix")


def _execute_command(client, cmd: str, args: list[str], limit: int) -> Any:
    if cmd == "get":
        return client.get(args[0])
    if cmd == "mget":
        return client.mget(args)
    if cmd == "hget":
        return client.hget(args[0], args[1])
    if cmd == "hgetall":
        return client.hgetall(args[0])
    if cmd == "hscan":
        cursor = int(args[1]) if len(args) > 1 else 0
        return client.hscan(args[0], cursor=cursor, count=limit)
    if cmd == "lrange":
        return client.lrange(args[0], int(args[1]), int(args[2]))
    if cmd == "zrange":
        return client.zrange(args[0], int(args[1]), int(args[2]), withscores=True)
    if cmd == "zrevrange":
        return client.zrevrange(args[0], int(args[1]), int(args[2]), withscores=True)
    if cmd == "sscan":
        cursor = int(args[1]) if len(args) > 1 else 0
        return client.sscan(args[0], cursor=cursor, count=limit)
    if cmd == "scan":
        cursor = int(args[0]) if args else 0
        match = None
        lowered = [token.lower() for token in args]
        if "match" in lowered:
            match_index = lowered.index("match")
            if len(args) > match_index + 1:
                match = args[match_index + 1]
        return client.scan(cursor=cursor, match=match, count=limit)
    if cmd == "type":
        return client.type(args[0])
    if cmd == "ttl":
        return client.ttl(args[0])
    if cmd == "exists":
        return client.exists(args[0])
    if cmd == "xlen":
        return client.xlen(args[0])
    if cmd == "xrange":
        return client.xrange(args[0], count=limit)
    if cmd == "xrevrange":
        return client.xrevrange(args[0], count=limit)
    raise ValueError("Command not supported")

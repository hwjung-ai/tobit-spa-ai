from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PostgresQueryRequest(BaseModel):
    sql: str = Field(..., min_length=1)


class Neo4jQueryRequest(BaseModel):
    cypher: str = Field(..., min_length=1)
    params: Optional[Dict[str, Any]] = None


class RedisCommandRequest(BaseModel):
    command: str = Field(..., min_length=1)


class GridResult(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]


class RedisKeyResult(BaseModel):
    key: str
    type: str
    ttl: Optional[int]
    value: Any

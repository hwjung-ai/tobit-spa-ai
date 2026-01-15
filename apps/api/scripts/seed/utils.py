from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver
from psycopg import Connection, connect

_ENV_PATH: Final[Path] = Path(__file__).resolve().parents[2] / ".env"
_env_loaded = False


def _load_env() -> None:
    global _env_loaded
    if not _env_loaded:
        load_dotenv(dotenv_path=_ENV_PATH)
        _env_loaded = True


def _env_value(key: str, default: str | None = None) -> str:
    value = os.environ.get(key)
    if not value and default is None:
        raise RuntimeError(f"Missing environment variable {key}")
    return value or default  # type: ignore[return-value]


def get_postgres_conn() -> Connection:
    _load_env()
    return connect(
        host=_env_value("PG_HOST"),
        port=int(_env_value("PG_PORT", "5432")),
        dbname=_env_value("PG_DB"),
        user=_env_value("PG_USER"),
        password=_env_value("PG_PASSWORD"),
        options="-c timezone=UTC",
    )


def get_neo4j_driver() -> Driver:
    _load_env()
    uri = _env_value("NEO4J_URI")
    user = _env_value("NEO4J_USER")
    password = _env_value("NEO4J_PASSWORD")
    return GraphDatabase.driver(uri, auth=(user, password))

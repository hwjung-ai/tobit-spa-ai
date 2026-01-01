from __future__ import annotations

from pathlib import Path
from typing import ClassVar, List, Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_env: str = "dev"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    log_level: str = "info"
    ops_mode: Literal["mock", "real"] = "mock"
    ops_enable_langgraph: bool = False
    enable_system_apis: bool = False

    cep_enable_metric_polling: bool = False
    cep_metric_poll_global_interval_seconds: int = 10
    cep_metric_poll_concurrency: int = 5
    cep_metric_http_timeout_seconds: float = 3.0
    cep_metric_poll_snapshot_interval_seconds: int = 60
    cep_enable_notifications: bool = False
    cep_notification_interval_seconds: int = 30

    pg_host: Optional[str] = None
    pg_port: int = 5432
    pg_db: Optional[str] = None
    pg_user: Optional[str] = None
    pg_password: Optional[str] = None
    database_url: Optional[str] = None

    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None

    redis_url: Optional[str] = None

    embed_model: Optional[str] = None
    chat_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    embedding_dimension: int = 1536
    document_storage_root: Optional[Path] = None

    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = None
    langsmith_tracing: bool = False

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    connection_cache: ClassVar[dict[str, BaseSettings]] = {}

    @property
    def cors_allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def postgres_dsn(self) -> str:
        if self.database_url:
            return self.database_url
        if not all([self.pg_host, self.pg_db, self.pg_user, self.pg_password]):
            raise ValueError("Postgres configuration requires host, db, user, password")
        return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"

    @property
    def document_storage_path(self) -> Path:
        base = (
            self.document_storage_root
            or Path(__file__).resolve().parents[1] / "storage"
        )
        return base.expanduser()

    @classmethod
    def cached_settings(cls) -> "AppSettings":
        if (cached := cls.connection_cache.get("default")) is None:
            cached = cls()
            cls.connection_cache["default"] = cached
        return cached


def get_settings() -> AppSettings:
    return AppSettings.cached_settings()

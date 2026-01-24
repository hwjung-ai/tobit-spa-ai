from __future__ import annotations

from pathlib import Path
from typing import ClassVar, List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_env: str = "dev"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    log_level: str = "info"
    ops_mode: Literal["mock", "real"] = "mock"
    ops_enable_langgraph: bool = False
    enable_system_apis: bool = False
    enable_data_explorer: bool = False
    ops_default_source_asset: str | None = None
    ops_default_schema_asset: str | None = None
    ops_default_resolver_asset: str | None = None

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
    data_pg_allow_schemas: str = "public"
    data_pg_allow_tables: str = "tb_cep_*,tb_api_*,ci,ci_ext,event_log"
    data_redis_allowed_prefixes: str = "cep:"
    data_max_rows: int = 200
    data_query_timeout_ms: int = 3000
    ops_enable_cep_scheduler: bool = False

    embed_model: Optional[str] = None
    chat_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    embedding_dimension: int = 1536
    document_storage_root: Optional[Path] = Field(default=None, env="DOCUMENT_STORAGE_ROOT")

    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = None
    langsmith_tracing: bool = False

    # Authentication settings
    enable_auth: bool = False  # Toggle authentication on/off for debugging
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # HTTPS & Security Headers settings
    https_enabled: bool = False
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    https_redirect: bool = True
    security_headers_enabled: bool = True
    csrf_protection_enabled: bool = True
    csrf_trusted_origins: str = "http://localhost:3000"
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True

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
    def csrf_trusted_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.csrf_trusted_origins.split(",") if origin.strip()]

    @property
    def postgres_dsn(self) -> str:
        if self.database_url:
            return self.database_url
        if not all([self.pg_host, self.pg_db, self.pg_user, self.pg_password]):
            raise ValueError("Postgres configuration requires host, db, user, password")
        return f"postgresql+psycopg://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"

    def _normalize_psycopg_dsn(self, value: str) -> str:
        prefix = "postgresql+psycopg://"
        if value.startswith(prefix):
            return "postgresql://" + value[len(prefix) :]
        return value

    @property
    def psycopg_dsn(self) -> str:
        """
        psycopg 3 expects a plain libpq-style DSN, so strip the SQLAlchemy dialect hint.
        """
        if self.database_url:
            return self._normalize_psycopg_dsn(self.database_url)
        if not all([self.pg_host, self.pg_db, self.pg_user, self.pg_password]):
            raise ValueError("Postgres configuration requires host, db, user, password")
        dsn = f"postgresql+psycopg://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        return self._normalize_psycopg_dsn(dsn)

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

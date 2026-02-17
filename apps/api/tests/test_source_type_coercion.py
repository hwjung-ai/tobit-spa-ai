from app.modules.asset_registry.source_models import (
    SourceType,
    coerce_source_connection,
    coerce_source_type,
)


def test_coerce_source_type_maps_legacy_postgres() -> None:
    assert coerce_source_type("postgres") == SourceType.POSTGRESQL


def test_coerce_source_type_defaults_to_postgresql_for_unknown() -> None:
    assert coerce_source_type("unknown-legacy-type") == SourceType.POSTGRESQL


def test_coerce_source_connection_supports_env_placeholder_port() -> None:
    connection = coerce_source_connection({"host": "db", "port": "${DB_PORT:5432}"})
    assert connection.port == 5432

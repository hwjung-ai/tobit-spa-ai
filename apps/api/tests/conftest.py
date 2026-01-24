"""Test configuration and fixtures."""

import importlib
import sys
from pathlib import Path

import pytest

# Add the app root to sys.path so imports work correctly
app_root = Path(__file__).parent.parent
sys.path.insert(0, str(app_root))

# Also add parent directory for 'apps' package
apps_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(apps_root))


def _patch_jsonb_for_sqlite(metadata):
    """Patch JSONB to JSON for SQLite compatibility."""
    from sqlalchemy import JSON
    for table_name in list(metadata.tables.keys()):
        table = metadata.tables[table_name]
        for column in table.columns:
            if str(column.type).startswith("JSONB"):
                column.type = JSON()


@pytest.fixture
def test_engine():
    """Create a test database engine."""
    # Monkey patch JSONB to JSON for SQLite
    import sqlalchemy.dialects.postgresql
    from sqlalchemy import JSON, text
    from sqlmodel import SQLModel, create_engine
    from sqlmodel.pool import StaticPool
    sqlalchemy.dialects.postgresql.JSONB = JSON

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Clear and reload models to avoid metadata caching
    try:
        for table_name in list(SQLModel.metadata.tables.keys()):
            del SQLModel.metadata.tables[table_name]
    except Exception:
        pass

    # Import all models
    import app.modules.api_keys.models as apikeys_models  # noqa: F401
    import app.modules.asset_registry.models as asset_models  # noqa: F401
    import app.modules.audit_log.models as audit_models  # noqa: F401
    import app.modules.auth.models as auth_models  # noqa: F401
    import app.modules.ci_management.models as ci_models  # noqa: F401
    import app.modules.inspector.models as inspector_models  # noqa: F401
    import app.modules.operation_settings.models as settings_models  # noqa: F401
    import app.modules.permissions.models as perm_models  # noqa: F401

    importlib.reload(auth_models)
    importlib.reload(perm_models)
    importlib.reload(apikeys_models)
    importlib.reload(asset_models)
    importlib.reload(ci_models)
    importlib.reload(audit_models)
    importlib.reload(settings_models)
    importlib.reload(inspector_models)

    # Drop all existing tables
    with engine.connect() as conn:
        inspector = sqlalchemy.inspect(engine)
        for table_name in inspector.get_table_names():
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            except Exception:
                pass
        try:
            conn.commit()
        except Exception:
            pass

    # Create all tables
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        if "already exists" in str(e):
            # Handle metadata caching issue
            with engine.begin() as conn:
                for table in SQLModel.metadata.tables.values():
                    try:
                        table.create(conn, checkfirst=True)
                    except Exception:
                        pass
        else:
            raise

    yield engine


@pytest.fixture
def session(test_engine):
    """Create a test database session."""
    from sqlmodel import Session

    with Session(test_engine) as session:
        # Initialize operation settings for tests
        try:
            from app.modules.operation_settings.crud import create_or_update_setting
            # Create settings with default values
            settings_to_create = {
                "ops_mode": {"value": "mock", "restart_required": True},
                "ops_enable_langgraph": {"value": False, "restart_required": True},
                "enable_system_apis": {"value": False, "restart_required": False},
                "enable_data_explorer": {"value": False, "restart_required": False},
            }
            for setting_key, config in settings_to_create.items():
                create_or_update_setting(
                    session=session,
                    setting_key=setting_key,
                    setting_value={"value": config["value"]},
                    description=f"Test {setting_key}",
                    published_by="test_suite",
                    restart_required=config["restart_required"],
                )
        except Exception:
            # Ignore errors during initialization
            pass

        # Reset app dependency overrides for each test
        from main import app
        app.dependency_overrides.clear()

        yield session

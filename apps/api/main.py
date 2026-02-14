import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.routes.chat import router as chat_router
from api.routes.documents import router as document_router
from api.routes.health import router as health_router
from api.routes.hello import router as hello_router
from api.routes.history import router as history_router
from api.routes.threads import router as thread_router
from app.core.exception_handlers import register_exception_handlers
from app.modules.admin.routes.logs import router as admin_logs_router
from app.modules.admin_dashboard.router import router as admin_dashboard_router
from app.modules.ai.router import router as ai_router
from app.modules.api_keys.router import router as api_keys_router
from app.modules.api_manager.router import router as api_manager_router
from app.modules.api_manager.runtime_router import runtime_router
from app.modules.asset_registry.router import router as asset_registry_router
from app.modules.asset_registry.tool_router import router as tool_router
from app.modules.audit_log.router import router as audit_log_router
from app.modules.auth.router import router as auth_router
from app.modules.cep_builder import router as cep_builder_router
from app.modules.cep_builder.scheduler import start_scheduler, stop_scheduler
from app.modules.ci_management.router import router as ci_management_router
from app.modules.data_explorer import router as data_explorer_router
from app.modules.document_processor.router import router as document_processor_router
from app.modules.inspector.router import router as inspector_router
from app.modules.llm.router import router as llm_logs_router
from app.modules.operation_settings.router import router as operation_settings_router
from app.modules.ops.router import router as ops_router
from app.modules.ops.services.domain.registry_init import (
    initialize_domain_planners,  # noqa: E402
)
from app.modules.ops.services.orchestration.mappings.registry_init import (
    initialize_mappings,  # noqa: E402
)

# Initialize OPS tool registry
from app.modules.ops.services.orchestration.tools.registry_init import (
    initialize_tools,  # noqa: E402
)
from app.modules.permissions.router import router as permissions_router
from app.modules.simulation.router import router as simulation_router
from app.shared import config_loader
from app.workers.api import router as workers_router
from core.auth import get_current_user
from core.config import get_settings
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.core.cors_config import CORSConfig
from apps.api.core.logging import configure_logging
from apps.api.core.middleware import RequestIDMiddleware
from apps.api.core.security_middleware import add_security_middleware

# Note: initialize_domain_planners() and initialize_tools() are now called in on_startup()
# to avoid duplicate initialization during uvicorn reload

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(redirect_slashes=False)
app.add_middleware(RequestIDMiddleware)
add_security_middleware(app, settings)

# Register global exception handlers
register_exception_handlers(app)

# Configure CORS with advanced settings
cors_config = CORSConfig(settings)
app.add_middleware(
    CORSMiddleware,
    **cors_config.get_cors_config_dict(),
)

# Unified API authentication dependency:
# all business routes require JWT (or debug user when ENABLE_AUTH=false).
auth_required = [Depends(get_current_user)]

app.include_router(health_router, dependencies=auth_required)
app.include_router(hello_router, dependencies=auth_required)
# Keep public auth entrypoints (/auth/login, /auth/refresh) unauthenticated.
app.include_router(admin_dashboard_router, dependencies=auth_required)
app.include_router(admin_logs_router, prefix="/admin", dependencies=auth_required)
app.include_router(auth_router)
app.include_router(api_keys_router, dependencies=auth_required)
app.include_router(permissions_router, dependencies=auth_required)
app.include_router(simulation_router, dependencies=auth_required)
app.include_router(workers_router, dependencies=auth_required, prefix="/api")
app.include_router(chat_router, dependencies=auth_required)
app.include_router(thread_router, dependencies=auth_required)
app.include_router(document_router, dependencies=auth_required)
app.include_router(document_processor_router, dependencies=auth_required)
app.include_router(ops_router, dependencies=auth_required)
app.include_router(asset_registry_router, dependencies=auth_required)
app.include_router(tool_router, dependencies=auth_required)
app.include_router(operation_settings_router, dependencies=auth_required)
app.include_router(cep_builder_router, dependencies=auth_required)
app.include_router(ci_management_router, dependencies=auth_required)
app.include_router(data_explorer_router, dependencies=auth_required)
app.include_router(audit_log_router, dependencies=auth_required)
app.include_router(api_manager_router, dependencies=auth_required)
app.include_router(runtime_router, dependencies=auth_required)
app.include_router(inspector_router, dependencies=auth_required)
app.include_router(ai_router, dependencies=auth_required)
app.include_router(llm_logs_router, prefix="/admin", dependencies=auth_required)
app.include_router(history_router, dependencies=auth_required)

_startup_task: asyncio.Task | None = None
_startup_ready = False
_startup_error: str | None = None


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _should_defer_heavy_startup() -> bool:
    # In dev, prioritize fast reload/startup unless explicitly disabled.
    env_flag = os.environ.get("DEFER_HEAVY_STARTUP")
    if env_flag is not None:
        return _is_truthy(env_flag, default=False)
    app_env = os.environ.get("APP_ENV", "dev").strip().lower()
    return app_env in {"dev", "local"}


def _run_migrations(logger) -> None:
    # Load .env file into os.environ for secret resolution
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
    enable_auto_migrate = _is_truthy(
        os.environ.get("ENABLE_AUTO_MIGRATE"), default=True
    )
    if not enable_auto_migrate:
        logger.info("Auto-migration disabled (ENABLE_AUTO_MIGRATE=false)")
        return
    try:
        from alembic import command
        from alembic.config import Config as AlembicConfig

        alembic_cfg = AlembicConfig("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.postgres_dsn)
        try:
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations completed successfully")
        except Exception as upgrade_error:
            if settings.app_env == "prod":
                logger.critical(
                    "Database migration failed in production - aborting startup: %s",
                    upgrade_error,
                    exc_info=True,
                )
                raise SystemExit(1) from upgrade_error
            else:
                logger.warning(
                    "Database migration failed in non-production environment (continuing): %s",
                    upgrade_error,
                )
                logger.info("Proceeding with current database schema")
    except Exception as migration_error:
        logger.error(
            "Failed to initialize migrations: %s", migration_error, exc_info=True
        )


def _run_heavy_startup_sync(logger) -> None:
    logger.info("Startup: Initializing OPS domain planners...")
    initialize_domain_planners()
    logger.info("Startup: OPS domain planners initialized.")

    logger.info("Startup: Initializing OPS tools...")
    initialize_tools()
    logger.info("Startup: OPS tools initialized.")

    logger.info("Startup: Initializing OPS mappings...")
    initialize_mappings()
    logger.info("Startup: OPS mappings initialized.")

    logger.info("Startup: Starting runtime tool discovery system...")
    import asyncio

    from app.modules.ops.services.orchestration.tools.runtime_tool_discovery import (
        start_runtime_discovery,
    )

    # Run in asyncio context for async startup
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            start_runtime_discovery(
                scan_interval=60,  # 1 minute
                webhook_enabled=True,
                auto_refresh=True
            )
        )
    finally:
        loop.close()

    logger.info("Startup: Runtime tool discovery system started.")

    _run_migrations(logger)

    logger.info("Startup: Starting CEP scheduler...")
    start_scheduler()
    logger.info("Startup: CEP scheduler started.")

    enable_watcher = _is_truthy(
        os.environ.get("ENABLE_RESOURCE_WATCHER"), default=True
    )
    logger.info("Startup: Starting resource watcher (enabled=%s)...", enable_watcher)
    config_loader.start_watching(enable_watcher)
    logger.info("Startup: Resource watcher started.")


async def _run_heavy_startup(logger) -> None:
    global _startup_ready, _startup_error
    try:
        await asyncio.to_thread(_run_heavy_startup_sync, logger)
        _startup_ready = True
        _startup_error = None
        logger.info("Startup: Heavy initialization completed.")
    except Exception as startup_error:
        _startup_ready = False
        _startup_error = str(startup_error)
        logger.error(
            "Startup: Heavy initialization failed: %s", startup_error, exc_info=True
        )


@app.on_event("startup")
async def on_startup() -> None:
    global _startup_task, _startup_ready, _startup_error

    import logging
    logger = logging.getLogger(__name__)
    _startup_ready = False
    _startup_error = None

    if _should_defer_heavy_startup():
        logger.info(
            "Startup: Deferring heavy initialization to background task (DEFER_HEAVY_STARTUP=true)."
        )
        _startup_task = asyncio.create_task(_run_heavy_startup(logger))
    else:
        logger.info("Startup: Running heavy initialization synchronously.")
        await _run_heavy_startup(logger)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _startup_task

    import logging
    logger = logging.getLogger(__name__)

    if _startup_task and not _startup_task.done():
        logger.info("Shutdown: Cancelling pending startup task...")
        _startup_task.cancel()
        try:
            await _startup_task
        except asyncio.CancelledError:
            pass
        _startup_task = None

    logger.info("Shutdown: Stopping runtime tool discovery system...")
    try:
        from app.modules.ops.services.orchestration.tools.runtime_tool_discovery import (
            get_runtime_discovery,
        )
        discovery = get_runtime_discovery()
        await discovery.stop_discovery()
        logger.info("Shutdown: Runtime tool discovery system stopped.")
    except Exception as e:
        logger.warning(f"Failed to stop runtime discovery: {str(e)}")

    logger.info("Shutdown: Stopping CEP scheduler...")
    # Stop CEP scheduler (now async)
    await stop_scheduler()
    logger.info("Shutdown: CEP scheduler stopped.")

    logger.info("Shutdown: Stopping resource watcher...")
    # Stop resource watcher
    config_loader.stop_watching()
    logger.info("Shutdown: Resource watcher stopped.")

    logger.info("Shutdown: All cleanup complete.")


@app.get("/health")
def health():
    """Public health check endpoint for Kubernetes probes (no auth required)."""
    global _startup_ready, _startup_error

    # Determine overall status based on startup and DB connection
    status = "up"
    message = "OK"

    if not _startup_ready:
        if _startup_error:
            status = "degraded"
            message = f"Startup failed: {_startup_error}"
        else:
            status = "starting"
            message = "Startup in progress"

    # Check actual DB connection
    postgres_connected = False
    postgres_error = None
    try:
        from core.db import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            postgres_connected = True
    except Exception as e:
        postgres_error = str(e)
        status = "degraded"
        message = f"Database unavailable: {postgres_error}"

    return {
        "time": datetime.utcnow().isoformat(),
        "code": 0,
        "message": message,
        "data": {
            "status": status,
            "startup": {
                "ready": _startup_ready,
                "in_progress": _startup_task is not None and not _startup_task.done(),
                "error": _startup_error,
            },
            "postgres": {
                "connected": postgres_connected,
                "error": postgres_error,
            },
        },
    }


@app.get("/hello")
def hello(_current_user=Depends(get_current_user)):
    return {
        "time": datetime.utcnow().isoformat(),
        "code": 0,
        "message": "OK",
        "data": {"hello": "tobit-spa-ai"},
    }

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
from app.modules.admin_dashboard.router import router as admin_dashboard_router
from app.modules.admin.routes.logs import router as admin_logs_router
from app.modules.api_keys.router import router as api_keys_router
from app.modules.api_manager.router import router as api_manager_router
from app.modules.api_manager.runtime_router import runtime_router
from app.modules.asset_registry.router import router as asset_registry_router
from app.modules.asset_registry.tool_router import router as tool_router
from app.modules.audit_log.router import router as audit_log_router
from app.modules.auth.router import router as auth_router
from app.modules.cep_builder import router as cep_builder_router
from app.modules.cep_builder.scheduler import start_scheduler, stop_scheduler
from app.modules.data_explorer import router as data_explorer_router
from app.modules.inspector.router import router as inspector_router
from app.modules.operation_settings.router import router as operation_settings_router
from app.modules.ops import router as ops_router

# Initialize OPS tool registry
from app.modules.ops.services.ci.tools.registry_init import (
    initialize_tools,  # noqa: E402
)
from app.modules.ops.services.ci.mappings.registry_init import (
    initialize_mappings,  # noqa: E402
)
from app.modules.ops.services.domain.registry_init import (
    initialize_domain_planners,  # noqa: E402
)

from app.modules.ci_management.router import router as ci_management_router
from app.modules.permissions.router import router as permissions_router
from app.shared import config_loader
from core.config import get_settings
from fastapi import FastAPI
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

# Configure CORS with advanced settings
cors_config = CORSConfig(settings)
app.add_middleware(
    CORSMiddleware,
    **cors_config.get_cors_config_dict(),
)
app.include_router(health_router)
app.include_router(hello_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_logs_router, prefix="/admin")
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(permissions_router)
app.include_router(chat_router)
app.include_router(thread_router)
app.include_router(document_router)
app.include_router(ops_router)
app.include_router(asset_registry_router)
app.include_router(tool_router)
app.include_router(operation_settings_router)
app.include_router(cep_builder_router)
app.include_router(ci_management_router)
app.include_router(data_explorer_router)
app.include_router(audit_log_router)
app.include_router(api_manager_router)
app.include_router(runtime_router)
app.include_router(inspector_router)
app.include_router(history_router)


@app.on_event("startup")
async def on_startup() -> None:
    import logging
    logger = logging.getLogger(__name__)

    # Initialize OPS domain registry (before tools, as tools may depend on domains)
    logger.info("Startup: Initializing OPS domain planners...")
    initialize_domain_planners()
    logger.info("Startup: OPS domain planners initialized.")

    # Initialize OPS tool registry
    logger.info("Startup: Initializing OPS tools...")
    initialize_tools()
    logger.info("Startup: OPS tools initialized.")

    # Initialize OPS mapping registry
    logger.info("Startup: Initializing OPS mappings...")
    initialize_mappings()
    logger.info("Startup: OPS mappings initialized.")

    # Load .env file into os.environ for secret resolution
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
    # Run database migrations (auto-upgrade on startup)
    enable_auto_migrate = os.environ.get("ENABLE_AUTO_MIGRATE", "true").lower() == "true"
    if enable_auto_migrate:
        try:
            from alembic import command
            from alembic.config import Config as AlembicConfig

            alembic_cfg = AlembicConfig("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", settings.postgres_dsn)

            try:
                command.upgrade(alembic_cfg, "head")
                logger.info("Database migrations completed successfully")
            except Exception as upgrade_error:
                logger.warning(
                    f"Migration upgrade failed (non-fatal): {upgrade_error}"
                )
                logger.info("Proceeding with current database schema")
        except Exception as e:
            logger.error(f"Failed to initialize migrations: {e}", exc_info=True)
    else:
        logger.info("Auto-migration disabled (ENABLE_AUTO_MIGRATE=false)")

    # Start CEP scheduler
    logger.info("Startup: Starting CEP scheduler...")
    start_scheduler()
    logger.info("Startup: CEP scheduler started.")

    # Start resource watcher
    enable_watcher = os.environ.get("ENABLE_RESOURCE_WATCHER", "true").lower() == "true"
    logger.info(f"Startup: Starting resource watcher (enabled={enable_watcher})...")
    config_loader.start_watching(enable_watcher)
    logger.info("Startup: Resource watcher started.")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    import logging
    logger = logging.getLogger(__name__)

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
    return {
        "time": datetime.utcnow().isoformat(),
        "code": 0,
        "message": "OK",
        "data": {"status": "up"},
    }


@app.get("/hello")
def hello():
    return {
        "time": datetime.utcnow().isoformat(),
        "code": 0,
        "message": "OK",
        "data": {"hello": "tobit-spa-ai"},
    }

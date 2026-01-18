import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.api_keys.router import router as api_keys_router
from app.modules.api_manager.router import router as api_manager_router
from app.modules.api_manager.runtime_router import runtime_router
from app.modules.asset_registry.router import router as asset_registry_router
from app.modules.auth.router import router as auth_router
from app.modules.audit_log.router import router as audit_log_router
from app.modules.cep_builder import router as cep_builder_router
from app.modules.operation_settings.router import router as operation_settings_router
from app.modules.cep_builder.scheduler import start_scheduler, stop_scheduler
from app.modules.data_explorer import router as data_explorer_router
from app.modules.inspector.router import router as inspector_router
from app.modules.ui_creator.router import router as ui_creator_router
from app.shared import config_loader
from api.routes.chat import router as chat_router
from api.routes.documents import router as document_router
from api.routes.health import router as health_router
from api.routes.hello import router as hello_router
from api.routes.history import router as history_router
from app.modules.ops.router import router as ops_router
from api.routes.threads import router as thread_router
from core.config import get_settings
from apps.api.core.logging import configure_logging
from apps.api.core.middleware import RequestIDMiddleware

# Initialize OPS tool registry
from app.modules.ops.services.ci.tools.registry_init import initialize_tools  # noqa: E402
initialize_tools()

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI()
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(hello_router)
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(chat_router)
app.include_router(thread_router)
app.include_router(document_router)
app.include_router(ops_router)
app.include_router(asset_registry_router)
app.include_router(operation_settings_router)
app.include_router(cep_builder_router)
app.include_router(data_explorer_router)
app.include_router(audit_log_router)
app.include_router(api_manager_router)
app.include_router(runtime_router)
app.include_router(ui_creator_router)
app.include_router(inspector_router)
app.include_router(history_router)


@app.on_event("startup")
async def on_startup() -> None:
    # Run database migrations
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command
        import logging

        logger = logging.getLogger(__name__)
        alembic_cfg = AlembicConfig("alembic.ini")

        # Set the actual database URL from settings instead of hardcoded alembic.ini
        alembic_cfg.set_main_option("sqlalchemy.url", settings.postgres_dsn)

        # Try to upgrade migrations - skip if alembic has conflicts
        try:
            # Try with explicit target first
            command.upgrade(alembic_cfg, "0031_add_auth_tables")
            logger.info("Database migrations completed successfully")
        except Exception as upgrade_error:
            # If explicit target fails, try current version
            logger.warning(f"Migration with explicit target failed: {upgrade_error}")
            logger.info("Proceeding with current database schema")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to initialize migrations: {e}", exc_info=True)

    # Start CEP scheduler
    start_scheduler()
    # Start resource watcher
    enable_watcher = os.environ.get("ENABLE_RESOURCE_WATCHER", "true").lower() == "true"
    config_loader.start_watching(enable_watcher)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    # Stop CEP scheduler
    stop_scheduler()
    # Stop resource watcher
    config_loader.stop_watching()


@app.get("/health")
def health():
    return {"time": datetime.utcnow().isoformat(), "code": 0, "message": "OK", "data": {"status": "up"}}


@app.get("/hello")
def hello():
    return {"time": datetime.utcnow().isoformat(), "code": 0, "message": "OK", "data": {"hello": "tobit-spa-ai"}}

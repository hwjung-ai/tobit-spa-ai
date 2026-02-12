from core.config import get_settings
from fastapi import APIRouter
from schemas.common import ResponseEnvelope
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
def health():
    settings = get_settings()

    # Check if PostgreSQL is configured
    postgres_configured = bool(
        settings.pg_host
        and settings.pg_db
        and settings.pg_user
        and settings.pg_password
    )

    # Check actual PostgreSQL connection
    postgres_connected = False
    postgres_error = None

    if postgres_configured:
        try:
            from core.db import engine
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                postgres_connected = True
        except Exception as e:
            postgres_error = str(e)

    # Determine overall status
    if postgres_connected:
        overall_status = "up"
        overall_message = "Healthy"
    elif postgres_configured:
        overall_status = "degraded"
        overall_message = f"Database unavailable: {postgres_error}"
    else:
        overall_status = "down"
        overall_message = "Database not configured"

    return ResponseEnvelope.success(
        data={
            "status": overall_status,
            "env": settings.app_env,
            "postgres": {
                "configured": postgres_configured,
                "connected": postgres_connected,
                "error": postgres_error,
            },
        },
        message=overall_message,
    )

from core.config import get_settings
from fastapi import APIRouter
from schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("/health")
def health():
    settings = get_settings()
    return ResponseEnvelope.success(
        data={
            "status": "up",
            "env": settings.app_env,
            "postgres": bool(
                settings.pg_host
                and settings.pg_db
                and settings.pg_user
                and settings.pg_password
            ),
        },
        message="Healthy",
    )

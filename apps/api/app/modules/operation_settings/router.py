from __future__ import annotations

from typing import Any, Dict

from core.config import get_settings
from core.db import get_session
from core.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.operation_settings.services import OperationSettingsService

router = APIRouter(prefix="/settings", tags=["settings"])
logger = get_logger(__name__)


@router.get("/operations")
def get_all_operation_settings(
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get all operation settings with their effective values and sources.

    Returns settings with priority resolution:
    - published > env > default
    """
    try:
        app_settings = get_settings()
        settings = OperationSettingsService.get_all_settings(session, app_settings)
        logger.info("operation_settings.get_all", extra={"count": len(settings)})
        return ResponseEnvelope.success(data={"settings": settings})
    except Exception as exc:
        logger.exception("operation_settings.get_all.error", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/operations/{setting_key}")
def get_operation_setting(
    setting_key: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get a specific operation setting with its effective value and source.

    Returns:
    - value: the effective value
    - source: where the value came from (published/env/default)
    - restart_required: whether a restart is needed
    - description: setting description
    - default: default value
    - allowed_values: list of allowed values if applicable
    """
    try:
        app_settings = get_settings()
        setting = OperationSettingsService.get_setting(session, setting_key, app_settings)
        logger.info("operation_settings.get", extra={"setting_key": setting_key, "source": setting["source"]})
        return ResponseEnvelope.success(data=setting)
    except ValueError as exc:
        logger.warning("operation_settings.get.invalid", extra={"setting_key": setting_key, "error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("operation_settings.get.error", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/operations/{setting_key}")
def update_operation_setting(
    setting_key: str,
    payload: Dict[str, Any],
    updated_by: str = Query("admin", description="User making the change"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Update an operation setting.

    The new value will be published to the database, creating an audit log entry.

    Request body:
    {
        "value": <new_value>
    }

    Returns:
    - key: the setting key
    - value: the new value
    - source: "published" (new value is published)
    - restart_required: whether a restart is needed
    - published_by: who made the change
    - published_at: when the change was made
    """
    try:
        if "value" not in payload:
            raise ValueError("Request must include 'value' field")

        new_value = payload["value"]

        # Update the setting (this will create audit log entry automatically)
        updated_setting = OperationSettingsService.update_setting(
            session=session,
            setting_key=setting_key,
            new_value=new_value,
            updated_by=updated_by,
        )

        logger.info(
            "operation_settings.update",
            extra={
                "setting_key": setting_key,
                "new_value": new_value,
                "restart_required": updated_setting["restart_required"],
                "updated_by": updated_by,
            },
        )

        return ResponseEnvelope.success(data=updated_setting)

    except ValueError as exc:
        logger.warning(
            "operation_settings.update.invalid",
            extra={"setting_key": setting_key, "error": str(exc)},
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(
            "operation_settings.update.error",
            exc_info=exc,
        )
        raise HTTPException(status_code=500, detail=str(exc))

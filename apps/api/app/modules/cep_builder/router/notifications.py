"""Notification management endpoints for CEP Builder."""

from __future__ import annotations

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.common import ResponseEnvelope
from sqlmodel import Session

from ..crud import (
    create_notification,
    get_notification,
    list_notification_logs,
    list_notifications,
    update_notification,
)
from ..schemas import (
    CepNotificationCreate,
    CepNotificationLogRead,
    CepNotificationRead,
    CepNotificationUpdate,
)

router = APIRouter(prefix="/cep/notifications", tags=["cep-notifications"])


@router.get("")
def list_notifications_endpoint(
    active_only: bool = Query(True),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """List all CEP notifications."""
    notifications = list_notifications(session, active_only=active_only)
    payload = [
        CepNotificationRead.from_orm(notification).model_dump()
        for notification in notifications
    ]
    return ResponseEnvelope.success(data={"notifications": payload})


@router.get("/{notification_id}")
def get_notification_endpoint(
    notification_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    """Get a single notification by ID."""
    notification = get_notification(session, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return ResponseEnvelope.success(
        data={"notification": CepNotificationRead.from_orm(notification).model_dump()}
    )


@router.post("")
def create_notification_endpoint(
    payload: CepNotificationCreate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Create a new CEP notification."""
    notification = create_notification(session, payload.model_dump())
    return ResponseEnvelope.success(
        data={"notification": CepNotificationRead.from_orm(notification).model_dump()}
    )


@router.put("/{notification_id}")
def update_notification_endpoint(
    notification_id: str,
    payload: CepNotificationUpdate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Update an existing CEP notification."""
    notification = get_notification(session, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    update_payload = payload.model_dump(exclude_unset=True)
    updated = update_notification(session, notification, update_payload)
    return ResponseEnvelope.success(
        data={"notification": CepNotificationRead.from_orm(updated).model_dump()}
    )


@router.get("/{notification_id}/logs")
def get_notification_logs_endpoint(
    notification_id: str,
    limit: int = Query(200, ge=1, le=500),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get notification logs for a specific notification."""
    notification = get_notification(session, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    logs = list_notification_logs(session, notification_id, limit=limit)
    payload = [CepNotificationLogRead.from_orm(log).model_dump() for log in logs]
    return ResponseEnvelope.success(data={"logs": payload})

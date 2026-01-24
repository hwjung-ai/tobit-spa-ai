"""API Keys management router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from apps.api.app.modules.api_keys.crud import (
    create_api_key,
    get_api_key,
    list_api_keys,
    revoke_api_key,
)
from apps.api.app.modules.api_keys.models import (
    TbApiKeyCreate,
)
from apps.api.app.modules.auth.models import TbUser
from apps.api.core.auth import get_current_user
from apps.api.core.db import get_session
from apps.api.schemas.common import ResponseEnvelope

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", response_model=ResponseEnvelope, status_code=status.HTTP_201_CREATED)
def create_new_api_key(
    payload: TbApiKeyCreate,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Create a new API key for the current user.

    Args:
        payload: API key creation payload
        session: Database session
        current_user: Current authenticated user

    Returns:
        ResponseEnvelope with created API key and the full key (shown only once)
    """
    api_key, full_key = create_api_key(
        session=session,
        user_id=current_user.id,
        name=payload.name,
        scope=payload.scope,
        expires_at=payload.expires_at,
        trace_id=getattr(current_user, "_trace_id", "system"),
    )

    return ResponseEnvelope.success(
        data={
            "api_key": {
                "id": api_key.id,
                "name": api_key.name,
                "key_prefix": api_key.key_prefix,
                "scope": api_key.scope,
                "is_active": api_key.is_active,
                "created_at": api_key.created_at.isoformat(),
                "expires_at": api_key.expires_at.isoformat()
                if api_key.expires_at
                else None,
            },
            "key": full_key,
            "warning": "⚠️  Save this key in a secure location. You won't be able to see it again.",
        }
    )


@router.get("", response_model=ResponseEnvelope)
def list_user_api_keys(
    include_inactive: bool = Query(False, description="Include inactive keys"),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    List all API keys for the current user.

    Args:
        include_inactive: Whether to include inactive keys
        session: Database session
        current_user: Current authenticated user

    Returns:
        ResponseEnvelope with list of API keys
    """
    api_keys = list_api_keys(
        session=session,
        user_id=current_user.id,
        include_inactive=include_inactive,
    )

    keys_data = [
        {
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "scope": key.scope,
            "is_active": key.is_active,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "created_at": key.created_at.isoformat(),
        }
        for key in api_keys
    ]

    return ResponseEnvelope.success(
        data={
            "api_keys": keys_data,
            "total": len(keys_data),
            "active": sum(1 for key in api_keys if key.is_active),
        }
    )


@router.get("/{key_id}", response_model=ResponseEnvelope)
def get_api_key_details(
    key_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get details of a specific API key.

    Args:
        key_id: API key ID
        session: Database session
        current_user: Current authenticated user

    Returns:
        ResponseEnvelope with API key details

    Raises:
        HTTPException: If key not found or user doesn't own the key
    """
    api_key = get_api_key(session, key_id, current_user.id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return ResponseEnvelope.success(
        data={
            "api_key": {
                "id": api_key.id,
                "name": api_key.name,
                "key_prefix": api_key.key_prefix,
                "scope": api_key.scope,
                "is_active": api_key.is_active,
                "last_used_at": api_key.last_used_at.isoformat()
                if api_key.last_used_at
                else None,
                "expires_at": api_key.expires_at.isoformat()
                if api_key.expires_at
                else None,
                "created_at": api_key.created_at.isoformat(),
                "created_by_trace_id": api_key.created_by_trace_id,
            }
        }
    )


@router.delete("/{key_id}", response_model=ResponseEnvelope)
def revoke_api_key_endpoint(
    key_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Revoke (deactivate) an API key.

    Args:
        key_id: API key ID
        session: Database session
        current_user: Current authenticated user

    Returns:
        ResponseEnvelope with confirmation

    Raises:
        HTTPException: If key not found or user doesn't own the key
    """
    success = revoke_api_key(session, key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return ResponseEnvelope.success(
        data={"message": f"API key {key_id} has been revoked"}
    )

"""Permissions management REST API router."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from apps.api.app.modules.auth.models import TbUser, UserRole
from apps.api.app.modules.permissions.crud import (
    check_permission,
    grant_resource_permission,
    list_user_permissions,
    revoke_resource_permission,
)
from apps.api.app.modules.permissions.models import ResourcePermission
from apps.api.core.auth import get_current_user, require_role
from apps.api.core.db import get_session
from apps.api.schemas.common import ResponseEnvelope

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.post("/check", response_model=ResponseEnvelope)
def check_permission_endpoint(
    user_id: str = Query(..., description="User to check"),
    permission: ResourcePermission = Query(..., description="Permission to check"),
    resource_type: Optional[str] = Query(None, description="Resource type"),
    resource_id: Optional[str] = Query(None, description="Resource ID"),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(require_role(UserRole.ADMIN)),
) -> ResponseEnvelope:
    """
    Check if a user has a specific permission.

    Admin-only endpoint for administrative purposes.

    Args:
        user_id: User to check
        permission: Permission to verify
        resource_type: Optional resource type
        resource_id: Optional specific resource ID
        session: Database session
        current_user: Current admin user

    Returns:
        PermissionCheck result
    """
    # Get user from database to check their role
    from sqlmodel import select

    from apps.api.app.modules.auth.models import TbUser as UserModel

    stmt = select(UserModel).where(UserModel.id == user_id)
    target_user = session.exec(stmt).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = check_permission(
        session=session,
        user_id=user_id,
        role=target_user.role,
        permission=permission,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    return ResponseEnvelope.success(
        data={
            "granted": result.granted,
            "reason": result.reason,
            "expires_at": result.expires_at.isoformat() if result.expires_at else None,
        }
    )


@router.get("/me", response_model=ResponseEnvelope)
def get_my_permissions(
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get all permissions for the current user.

    Returns both role-based and resource-specific permissions.

    Args:
        session: Database session
        current_user: Current authenticated user

    Returns:
        Permissions dict with role and resource overrides
    """
    perms = list_user_permissions(session, current_user.id, current_user.role)

    return ResponseEnvelope.success(
        data={
            "role_permissions": [p.value for p in perms["role_permissions"]],
            "resource_permissions": perms["resource_permissions"],
            "effective_permissions": len(perms["role_permissions"]) + len(perms["resource_permissions"]),
        }
    )


@router.get("/{user_id}", response_model=ResponseEnvelope)
def get_user_permissions(
    user_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(require_role(UserRole.MANAGER)),
) -> ResponseEnvelope:
    """
    Get all permissions for a specific user.

    Manager+ only (can view team member permissions).

    Args:
        user_id: User to get permissions for
        session: Database session
        current_user: Current manager user

    Returns:
        Permissions dict
    """
    # Get target user
    from sqlmodel import select

    from apps.api.app.modules.auth.models import TbUser as UserModel

    stmt = select(UserModel).where(UserModel.id == user_id)
    target_user = session.exec(stmt).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    perms = list_user_permissions(session, user_id, target_user.role)

    return ResponseEnvelope.success(
        data={
            "user_id": user_id,
            "username": target_user.username,
            "role": target_user.role.value,
            "role_permissions": [p.value for p in perms["role_permissions"]],
            "resource_permissions": perms["resource_permissions"],
        }
    )


@router.post("/grant", response_model=ResponseEnvelope, status_code=status.HTTP_201_CREATED)
def grant_permission(
    user_id: str = Query(..., description="User to grant permission to"),
    resource_type: str = Query(..., description="Resource type"),
    permission: ResourcePermission = Query(..., description="Permission to grant"),
    resource_id: Optional[str] = Query(None, description="Specific resource ID (None = all of type)"),
    expires_at: Optional[datetime] = Query(None, description="Optional expiration time"),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(require_role(UserRole.ADMIN)),
) -> ResponseEnvelope:
    """
    Grant a resource-specific permission to a user.

    Admin-only operation.

    Args:
        user_id: User to grant permission to
        resource_type: Type of resource
        permission: Permission to grant
        resource_id: Specific resource (None = all)
        expires_at: Optional expiration
        session: Database session
        current_user: Current admin user

    Returns:
        Created permission record
    """
    perm = grant_resource_permission(
        session=session,
        user_id=user_id,
        resource_type=resource_type,
        permission=permission,
        resource_id=resource_id,
        created_by_user_id=current_user.id,
        expires_at=expires_at,
    )

    return ResponseEnvelope.success(
        data={
            "permission_id": perm.id,
            "user_id": perm.user_id,
            "resource_type": perm.resource_type,
            "resource_id": perm.resource_id,
            "permission": perm.permission.value,
            "expires_at": perm.expires_at.isoformat() if perm.expires_at else None,
            "created_at": perm.created_at.isoformat(),
        },
        status_code=status.HTTP_201_CREATED,
    )


@router.delete("/revoke", response_model=ResponseEnvelope)
def revoke_permission(
    user_id: str = Query(..., description="User to revoke from"),
    resource_type: str = Query(..., description="Resource type"),
    permission: ResourcePermission = Query(..., description="Permission to revoke"),
    resource_id: Optional[str] = Query(None, description="Specific resource ID"),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(require_role(UserRole.ADMIN)),
) -> ResponseEnvelope:
    """
    Revoke a resource-specific permission.

    Admin-only operation.

    Args:
        user_id: User to revoke from
        resource_type: Resource type
        permission: Permission to revoke
        resource_id: Specific resource (None = all)
        session: Database session
        current_user: Current admin user

    Returns:
        Confirmation message
    """
    success = revoke_resource_permission(
        session=session,
        user_id=user_id,
        resource_type=resource_type,
        permission=permission,
        resource_id=resource_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    return ResponseEnvelope.success(
        data={
            "message": f"Revoked {permission.value} for {user_id} on {resource_type}",
        }
    )

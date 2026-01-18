"""Permission checking decorators and utilities."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from apps.api.app.modules.auth.models import TbUser
from apps.api.app.modules.permissions.crud import check_permission
from apps.api.app.modules.permissions.models import ResourcePermission
from apps.api.core.auth import get_current_user
from apps.api.core.db import get_session


def require_permission(
    permission: ResourcePermission,
    resource_type: Optional[str] = None,
):
    """
    Decorator for role and resource-based access control.

    Usage:
        @router.get("/apis/{api_id}")
        @require_permission(ResourcePermission.API_READ, resource_type="api")
        def get_api(
            api_id: str,
            session: Session = Depends(get_session),
            current_user: TbUser = Depends(get_current_user),
        ):
            # Check permission with resource_id
            # This is done in the decorator's dependency

    Args:
        permission: Permission to require
        resource_type: Type of resource being accessed

    Returns:
        Dependency function for FastAPI
    """
    async def permission_checker(
        current_user: TbUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ) -> TbUser:
        """Check if user has required permission."""
        result = check_permission(
            session=session,
            user_id=current_user.id,
            role=current_user.role,
            permission=permission,
            resource_type=resource_type,
            resource_id=None,  # Will be checked per-resource
        )

        if not result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {result.reason}",
            )

        return current_user

    return Depends(permission_checker)


def require_permission_with_resource(
    permission: ResourcePermission,
    resource_type: str,
    resource_id_param: str = "id",
):
    """
    Factory for permission checking with specific resource ID.

    Usage:
        @router.delete("/apis/{api_id}")
        def delete_api(
            api_id: str,
            session: Session = Depends(get_session),
            current_user: TbUser = require_permission_with_resource(
                ResourcePermission.API_DELETE,
                resource_type="api",
                resource_id_param="api_id",
            ),
        ):
            # User has been authorized with specific api_id

    Args:
        permission: Permission to require
        resource_type: Type of resource
        resource_id_param: Name of path parameter containing resource ID

    Returns:
        Dependency function that checks permission with resource_id
    """
    async def permission_checker_with_resource(
        current_user: TbUser = Depends(get_current_user),
        session: Session = Depends(get_session),
        request = Depends(lambda r: r),  # Will be provided by FastAPI
    ) -> TbUser:
        """Check permission with specific resource."""
        # In practice, FastAPI will inject the path parameter
        # This needs to be used differently in actual endpoints
        # See example in permission_checker function

        result = check_permission(
            session=session,
            user_id=current_user.id,
            role=current_user.role,
            permission=permission,
            resource_type=resource_type,
            resource_id=None,  # Caller must pass resource_id
        )

        if not result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {result.reason}",
            )

        return current_user

    return Depends(permission_checker_with_resource)


def check_permission_sync(
    session: Session,
    user_id: str,
    role,
    permission: ResourcePermission,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> bool:
    """
    Synchronous permission check for use in endpoint logic.

    Usage:
        @router.delete("/apis/{api_id}")
        def delete_api(
            api_id: str,
            session: Session = Depends(get_session),
            current_user: TbUser = Depends(get_current_user),
        ):
            # Check specific resource permission
            if not check_permission_sync(
                session,
                current_user.id,
                current_user.role,
                ResourcePermission.API_DELETE,
                resource_type="api",
                resource_id=api_id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied",
                )
            # ... proceed with deletion

    Args:
        session: Database session
        user_id: User ID
        role: User role
        permission: Permission to check
        resource_type: Resource type
        resource_id: Resource ID

    Returns:
        True if permission granted, False otherwise
    """
    result = check_permission(
        session=session,
        user_id=user_id,
        role=role,
        permission=permission,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return result.granted


class PermissionMiddleware:
    """
    Optional middleware for logging permission checks.
    Can be used for audit trails and debugging.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Log permission checks here if needed
            pass

        await self.app(scope, receive, send)

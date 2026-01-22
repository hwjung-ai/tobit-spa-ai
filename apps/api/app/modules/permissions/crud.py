"""CRUD operations for permission management."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Session, select

from apps.api.app.modules.auth.models import UserRole
from apps.api.app.modules.permissions.models import (
    PermissionCheck,
    ResourcePermission,
    RolePermissionDefault,
    TbResourcePermission,
    TbRolePermission,
)

# Default role permission sets
ROLE_PERMISSION_DEFAULTS = {
    RolePermissionDefault.ADMIN: [
        # Admin has ALL permissions
        *(list(ResourcePermission)),
    ],
    RolePermissionDefault.MANAGER: [
        # Manager has most permissions except user management
        ResourcePermission.API_READ,
        ResourcePermission.API_CREATE,
        ResourcePermission.API_UPDATE,
        ResourcePermission.API_EXECUTE,
        ResourcePermission.API_EXPORT,
        ResourcePermission.CI_READ,
        ResourcePermission.CI_CREATE,
        ResourcePermission.CI_UPDATE,
        ResourcePermission.CI_EXECUTE,
        ResourcePermission.CI_PAUSE,
        ResourcePermission.METRIC_READ,
        ResourcePermission.METRIC_EXPORT,
        ResourcePermission.GRAPH_READ,
        ResourcePermission.GRAPH_UPDATE,
        ResourcePermission.HISTORY_READ,
        ResourcePermission.CEP_READ,
        ResourcePermission.CEP_CREATE,
        ResourcePermission.CEP_UPDATE,
        ResourcePermission.CEP_EXECUTE,
        ResourcePermission.DOCUMENT_READ,
        ResourcePermission.DOCUMENT_UPLOAD,
        ResourcePermission.DOCUMENT_EXPORT,
        ResourcePermission.UI_READ,
        ResourcePermission.UI_CREATE,
        ResourcePermission.UI_UPDATE,
        ResourcePermission.ASSET_READ,
        ResourcePermission.ASSET_CREATE,
        ResourcePermission.ASSET_UPDATE,
        ResourcePermission.SETTINGS_READ,
        ResourcePermission.SETTINGS_UPDATE,
        ResourcePermission.AUDIT_READ,
        ResourcePermission.AUDIT_EXPORT,
    ],
    RolePermissionDefault.DEVELOPER: [
        # Developer has read and execute permissions
        ResourcePermission.API_READ,
        ResourcePermission.API_CREATE,
        ResourcePermission.API_UPDATE,
        ResourcePermission.API_EXECUTE,
        ResourcePermission.CI_READ,
        ResourcePermission.CI_CREATE,
        ResourcePermission.CI_UPDATE,
        ResourcePermission.CI_EXECUTE,
        ResourcePermission.METRIC_READ,
        ResourcePermission.GRAPH_READ,
        ResourcePermission.HISTORY_READ,
        ResourcePermission.CEP_READ,
        ResourcePermission.CEP_CREATE,
        ResourcePermission.CEP_UPDATE,
        ResourcePermission.CEP_EXECUTE,
        ResourcePermission.DOCUMENT_READ,
        ResourcePermission.DOCUMENT_UPLOAD,
        ResourcePermission.UI_READ,
        ResourcePermission.UI_CREATE,
        ResourcePermission.UI_UPDATE,
        ResourcePermission.ASSET_READ,
        ResourcePermission.ASSET_CREATE,
        ResourcePermission.ASSET_UPDATE,
        ResourcePermission.SETTINGS_READ,
    ],
    RolePermissionDefault.VIEWER: [
        # Viewer only has read permissions
        ResourcePermission.API_READ,
        ResourcePermission.METRIC_READ,
        ResourcePermission.GRAPH_READ,
        ResourcePermission.HISTORY_READ,
        ResourcePermission.CEP_READ,
        ResourcePermission.DOCUMENT_READ,
        ResourcePermission.UI_READ,
        ResourcePermission.ASSET_READ,
        ResourcePermission.SETTINGS_READ,
        ResourcePermission.AUDIT_READ,
    ],
}


def get_role_permissions(role: UserRole) -> list[ResourcePermission]:
    """
    Get all permissions for a role.

    Args:
        role: User role

    Returns:
        List of permissions
    """
    role_mapping = {
        UserRole.ADMIN: RolePermissionDefault.ADMIN,
        UserRole.MANAGER: RolePermissionDefault.MANAGER,
        UserRole.DEVELOPER: RolePermissionDefault.DEVELOPER,
        UserRole.VIEWER: RolePermissionDefault.VIEWER,
    }

    role_key = role_mapping.get(role, RolePermissionDefault.VIEWER)
    return ROLE_PERMISSION_DEFAULTS.get(role_key, [])


def initialize_role_permissions(session: Session) -> None:
    """
    Initialize default role permission mappings (run once at startup).

    Args:
        session: Database session
    """
    for role, permissions in ROLE_PERMISSION_DEFAULTS.items():
        for permission in permissions:
            # Check if already exists
            stmt = select(TbRolePermission).where(
                TbRolePermission.role == role,
                TbRolePermission.permission == permission,
            )

            existing = session.exec(stmt).first()
            if not existing:
                role_perm = TbRolePermission(
                    id=str(uuid4()),
                    role=role,
                    permission=permission,
                    is_granted=True,
                )
                session.add(role_perm)

    session.commit()


def check_permission(
    session: Session,
    user_id: str,
    role: UserRole,
    permission: ResourcePermission,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> PermissionCheck:
    """
    Check if user has a specific permission.

    Resolution order:
    1. Resource-specific override (expires_at checked)
    2. Role-based default permissions

    Args:
        session: Database session
        user_id: User ID
        role: User role
        permission: Permission to check
        resource_type: Type of resource being accessed
        resource_id: Specific resource ID

    Returns:
        PermissionCheck result with granted status and reason
    """
    # Check resource-specific permission first
    if resource_type and resource_id:
        stmt = select(TbResourcePermission).where(
            TbResourcePermission.user_id == user_id,
            TbResourcePermission.resource_type == resource_type,
            TbResourcePermission.resource_id == resource_id,
            TbResourcePermission.permission == permission,
        )

        resource_perm = session.exec(stmt).first()
        if resource_perm:
            # Check expiration
            if resource_perm.expires_at and resource_perm.expires_at <= datetime.now(timezone.utc):
                return PermissionCheck(
                    granted=False,
                    reason="Resource permission has expired",
                    expires_at=resource_perm.expires_at,
                )

            return PermissionCheck(
                granted=resource_perm.is_granted,
                reason=f"Resource-specific permission: {resource_perm.permission}",
                expires_at=resource_perm.expires_at,
            )

    # Check resource-type-level permission (resource_id=None)
    if resource_type:
        stmt = select(TbResourcePermission).where(
            TbResourcePermission.user_id == user_id,
            TbResourcePermission.resource_type == resource_type,
            TbResourcePermission.resource_id.is_(None),
            TbResourcePermission.permission == permission,
        )

        resource_perm = session.exec(stmt).first()
        if resource_perm:
            if resource_perm.expires_at and resource_perm.expires_at <= datetime.now(timezone.utc):
                return PermissionCheck(
                    granted=False,
                    reason="Resource type permission has expired",
                    expires_at=resource_perm.expires_at,
                )

            return PermissionCheck(
                granted=resource_perm.is_granted,
                reason=f"Resource-type permission: {resource_perm.permission}",
                expires_at=resource_perm.expires_at,
            )

    # Fall back to role-based permissions
    role_perms = get_role_permissions(role)

    if permission in role_perms:
        return PermissionCheck(
            granted=True,
            reason=f"Role-based permission: {role.value}",
        )

    return PermissionCheck(
        granted=False,
        reason=f"No permission granted for {permission.value}",
    )


def grant_resource_permission(
    session: Session,
    user_id: str,
    resource_type: str,
    permission: ResourcePermission,
    resource_id: Optional[str] = None,
    created_by_user_id: str = "system",
    expires_at: Optional[datetime] = None,
) -> TbResourcePermission:
    """
    Grant a resource-specific permission to a user.

    Args:
        session: Database session
        user_id: User to grant permission to
        resource_type: Type of resource
        permission: Permission to grant
        resource_id: Specific resource ID (None = all of type)
        created_by_user_id: User granting the permission
        expires_at: Optional expiration time

    Returns:
        TbResourcePermission record
    """
    perm = TbResourcePermission(
        id=str(uuid4()),
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        permission=permission,
        is_granted=True,
        expires_at=expires_at,
        created_by_user_id=created_by_user_id,
    )

    session.add(perm)
    session.commit()
    session.refresh(perm)

    return perm


def revoke_resource_permission(
    session: Session,
    user_id: str,
    resource_type: str,
    permission: ResourcePermission,
    resource_id: Optional[str] = None,
) -> bool:
    """
    Revoke a resource-specific permission.

    Args:
        session: Database session
        user_id: User to revoke from
        resource_type: Resource type
        permission: Permission to revoke
        resource_id: Specific resource ID (None = all of type)

    Returns:
        True if revoked, False if not found
    """
    stmt = select(TbResourcePermission).where(
        TbResourcePermission.user_id == user_id,
        TbResourcePermission.resource_type == resource_type,
        TbResourcePermission.permission == permission,
    )

    if resource_id:
        stmt = stmt.where(TbResourcePermission.resource_id == resource_id)
    else:
        stmt = stmt.where(TbResourcePermission.resource_id.is_(None))

    perm = session.exec(stmt).first()

    if not perm:
        return False

    session.delete(perm)
    session.commit()

    return True


def list_user_permissions(
    session: Session,
    user_id: str,
    role: UserRole,
) -> dict[str, list[ResourcePermission]]:
    """
    List all permissions for a user (role + resource-specific).

    Args:
        session: Database session
        user_id: User ID
        role: User role

    Returns:
        Dict with "role" and "resource_overrides" keys
    """
    role_perms = get_role_permissions(role)

    # Get resource-specific permissions
    stmt = select(TbResourcePermission).where(
        TbResourcePermission.user_id == user_id,
        TbResourcePermission.is_granted,
    )

    resource_perms = session.exec(stmt).all()

    return {
        "role_permissions": role_perms,
        "resource_permissions": [
            {
                "resource_type": p.resource_type,
                "resource_id": p.resource_id,
                "permission": p.permission.value,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in resource_perms
            if not p.expires_at or p.expires_at > datetime.now(timezone.utc)
        ],
    }

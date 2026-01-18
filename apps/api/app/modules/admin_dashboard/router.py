"""Admin dashboard API routes"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.auth import get_current_user
from .user_service import AdminUserService
from .system_monitor import SystemMonitor
from .settings_service import AdminSettingsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# Initialize services
user_service = AdminUserService()
system_monitor = SystemMonitor()
settings_service = AdminSettingsService()


class UserListRequest(BaseModel):
    """Request for listing users"""
    page: int = 1
    per_page: int = 20
    active_only: bool = False
    search: Optional[str] = None


class UserStatusUpdateRequest(BaseModel):
    """Request for updating user status"""
    is_active: bool


class PermissionRequest(BaseModel):
    """Request for permission changes"""
    permission: str
    reason: Optional[str] = None


class SettingUpdateRequest(BaseModel):
    """Request for updating a setting"""
    value: Any
    reason: Optional[str] = None


class SettingsBatchUpdateRequest(BaseModel):
    """Request for updating multiple settings"""
    settings: Dict[str, Any]
    reason: Optional[str] = None


@router.get("/users", response_model=dict)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    List users with filtering and pagination

    Filters:
    - active_only: Show only active users
    - search: Search by username or email
    """

    try:
        logger.info(
            f"Listing users: page={page}, per_page={per_page}, "
            f"active_only={active_only}, search={search}"
        )

        result = user_service.list_users(
            page=page,
            per_page=per_page,
            active_only=active_only,
            search=search,
        )

        return {
            "status": "ok",
            **result,
        }

    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/users/{user_id}", response_model=dict)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user details and permissions"""

    try:
        logger.info(f"Getting user details: {user_id}")

        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(404, f"User not found: {user_id}")

        permissions = user_service.get_user_permissions(user_id)

        return {
            "status": "ok",
            "user": user.to_dict(),
            "permissions": permissions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {str(e)}")
        raise HTTPException(500, str(e))


@router.patch("/users/{user_id}/status", response_model=dict)
async def update_user_status(
    user_id: str,
    request: UserStatusUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update user active status"""

    try:
        logger.info(f"Updating user {user_id} status: is_active={request.is_active}")

        user = user_service.update_user_status(user_id, request.is_active)
        if not user:
            raise HTTPException(404, f"User not found: {user_id}")

        return {
            "status": "ok",
            "message": f"User {user_id} {'activated' if request.is_active else 'deactivated'}",
            "user": user.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user status: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/users/{user_id}/permissions/grant", response_model=dict)
async def grant_permission(
    user_id: str,
    request: PermissionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Grant permission to user"""

    try:
        logger.info(
            f"Granting permission '{request.permission}' to user {user_id}, "
            f"reason: {request.reason}"
        )

        success = user_service.grant_permission(
            user_id=user_id,
            permission=request.permission,
            admin_id=current_user.get("id"),
            reason=request.reason,
        )

        if not success:
            return {
                "status": "ok",
                "message": f"User already has permission: {request.permission}",
            }

        return {
            "status": "ok",
            "message": f"Permission '{request.permission}' granted to user {user_id}",
            "permissions": user_service.get_user_permissions(user_id),
        }

    except Exception as e:
        logger.error(f"Failed to grant permission: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/users/{user_id}/permissions/revoke", response_model=dict)
async def revoke_permission(
    user_id: str,
    request: PermissionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Revoke permission from user"""

    try:
        logger.info(
            f"Revoking permission '{request.permission}' from user {user_id}, "
            f"reason: {request.reason}"
        )

        success = user_service.revoke_permission(
            user_id=user_id,
            permission=request.permission,
            admin_id=current_user.get("id"),
            reason=request.reason,
        )

        if not success:
            return {
                "status": "ok",
                "message": f"User doesn't have permission: {request.permission}",
            }

        return {
            "status": "ok",
            "message": f"Permission '{request.permission}' revoked from user {user_id}",
            "permissions": user_service.get_user_permissions(user_id),
        }

    except Exception as e:
        logger.error(f"Failed to revoke permission: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/users/{user_id}/audit-log", response_model=dict)
async def get_user_audit_log(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get permission audit log for a user"""

    try:
        logger.info(f"Getting audit log for user {user_id}")

        logs = user_service.get_permission_audit_log(user_id=user_id, limit=limit)

        return {
            "status": "ok",
            "user_id": user_id,
            "log_count": len(logs),
            "logs": logs,
        }

    except Exception as e:
        logger.error(f"Failed to get audit log: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/users/activity-summary", response_model=dict)
async def get_user_activity_summary(
    current_user: dict = Depends(get_current_user)
):
    """Get user activity summary"""

    try:
        logger.info("Getting user activity summary")

        summary = user_service.get_user_activity_summary()

        return {
            "status": "ok",
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"Failed to get activity summary: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/system/health", response_model=dict)
async def get_system_health(
    current_user: dict = Depends(get_current_user)
):
    """Get current system health status"""

    try:
        logger.info("Getting system health status")

        # Collect current metrics
        system_monitor.collect_resource_metrics()

        status = system_monitor.get_current_status()

        return {
            "status": "ok",
            "health": status,
        }

    except Exception as e:
        logger.error(f"Failed to get system health: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/system/metrics", response_model=dict)
async def get_system_metrics(
    limit: int = Query(288, ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """Get historical system metrics"""

    try:
        logger.info(f"Getting system metrics (limit={limit})")

        metrics = system_monitor.get_metrics_history(limit=limit)

        return {
            "status": "ok",
            "metrics": metrics,
        }

    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/system/alerts", response_model=dict)
async def get_system_alerts(
    severity: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get system alerts"""

    try:
        logger.info(f"Getting system alerts (severity={severity}, limit={limit})")

        alerts = system_monitor.get_alerts(severity=severity, limit=limit)

        return {
            "status": "ok",
            "alert_count": len(alerts),
            "alerts": alerts,
        }

    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/settings", response_model=dict)
async def get_settings(
    keys: Optional[List[str]] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get system settings"""

    try:
        logger.info(f"Getting settings (keys={keys})")

        settings = settings_service.get_settings(keys=keys)

        return {
            "status": "ok",
            "settings": settings,
        }

    except Exception as e:
        logger.error(f"Failed to get settings: {str(e)}")
        raise HTTPException(500, str(e))


@router.patch("/settings/{key}", response_model=dict)
async def update_setting(
    key: str,
    request: SettingUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a single setting"""

    try:
        logger.info(f"Updating setting {key}: {request.value}")

        success = settings_service.update_setting(
            key=key,
            value=request.value,
            admin_id=current_user.get("id"),
            reason=request.reason,
        )

        if not success:
            raise HTTPException(400, f"Failed to update setting: {key}")

        return {
            "status": "ok",
            "key": key,
            "value": request.value,
            "message": "Setting updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update setting: {str(e)}")
        raise HTTPException(500, str(e))


@router.patch("/settings", response_model=dict)
async def update_settings_batch(
    request: SettingsBatchUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update multiple settings"""

    try:
        logger.info(f"Updating {len(request.settings)} settings")

        results = settings_service.update_settings_batch(
            updates=request.settings,
            admin_id=current_user.get("id"),
            reason=request.reason,
        )

        successful = sum(1 for v in results.values() if v)

        return {
            "status": "ok",
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Failed to update settings: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/settings/reset-defaults", response_model=dict)
async def reset_settings_to_defaults(
    current_user: dict = Depends(get_current_user)
):
    """Reset all settings to defaults"""

    try:
        logger.warning("Resetting all settings to defaults")

        count = settings_service.reset_to_defaults(
            admin_id=current_user.get("id"),
            reason="Admin reset to defaults",
        )

        return {
            "status": "ok",
            "message": f"Reset {count} settings to defaults",
            "reset_count": count,
        }

    except Exception as e:
        logger.error(f"Failed to reset settings: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/settings/categories", response_model=dict)
async def get_settings_by_category(
    current_user: dict = Depends(get_current_user)
):
    """Get settings grouped by category"""

    try:
        logger.info("Getting settings by category")

        categories = settings_service.get_settings_by_category()

        return {
            "status": "ok",
            "categories": categories,
        }

    except Exception as e:
        logger.error(f"Failed to get settings by category: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/settings/audit-log", response_model=dict)
async def get_settings_audit_log(
    key: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get settings change audit log"""

    try:
        logger.info(f"Getting settings audit log (key={key}, limit={limit})")

        logs = settings_service.get_settings_audit_log(key=key, limit=limit)

        return {
            "status": "ok",
            "log_count": len(logs),
            "logs": logs,
        }

    except Exception as e:
        logger.error(f"Failed to get audit log: {str(e)}")
        raise HTTPException(500, str(e))

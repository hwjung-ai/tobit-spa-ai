"""Admin dashboard user management service"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UserActivity:
    """User activity tracking"""

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        last_login: Optional[datetime] = None,
        login_count: int = 0,
        is_active: bool = True,
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.last_login = last_login
        self.login_count = login_count
        self.is_active = is_active
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


class UserPermissionAudit:
    """Track permission changes"""

    def __init__(
        self,
        user_id: str,
        admin_id: str,
        action: str,  # grant, revoke, modify
        permission: str,
        reason: Optional[str] = None,
    ):
        self.user_id = user_id
        self.admin_id = admin_id
        self.action = action
        self.permission = permission
        self.reason = reason
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "admin_id": self.admin_id,
            "action": self.action,
            "permission": self.permission,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


class AdminUserService:
    """Admin service for user management"""

    def __init__(self):
        self.users: Dict[str, UserActivity] = {}
        self.audit_logs: List[UserPermissionAudit] = []
        self.user_permissions: Dict[str, List[str]] = {}

    def get_user(self, user_id: str) -> Optional[UserActivity]:
        """Get user details"""
        return self.users.get(user_id)

    def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
        active_only: bool = False,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List users with pagination and filtering"""

        users = list(self.users.values())

        # Filter by active status
        if active_only:
            users = [u for u in users if u.is_active]

        # Filter by search term (username or email)
        if search:
            search_lower = search.lower()
            users = [
                u for u in users
                if search_lower in u.username.lower() or search_lower in u.email.lower()
            ]

        # Sort by last login (newest first)
        users.sort(key=lambda u: u.last_login or datetime.min, reverse=True)

        # Paginate
        total = len(users)
        offset = (page - 1) * per_page
        paginated_users = users[offset : offset + per_page]

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "users": [u.to_dict() for u in paginated_users],
        }

    def update_user_status(self, user_id: str, is_active: bool) -> Optional[UserActivity]:
        """Update user active status"""
        user = self.users.get(user_id)
        if user:
            user.is_active = is_active
            logger.info(f"Updated user {user_id} active status to {is_active}")
        return user

    def record_login(self, user_id: str) -> bool:
        """Record user login"""
        user = self.users.get(user_id)
        if user:
            user.last_login = datetime.utcnow()
            user.login_count += 1
            return True
        return False

    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions"""
        return self.user_permissions.get(user_id, [])

    def grant_permission(
        self,
        user_id: str,
        permission: str,
        admin_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Grant permission to user"""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = []

        if permission not in self.user_permissions[user_id]:
            self.user_permissions[user_id].append(permission)

            # Record audit
            audit = UserPermissionAudit(
                user_id=user_id,
                admin_id=admin_id,
                action="grant",
                permission=permission,
                reason=reason,
            )
            self.audit_logs.append(audit)

            logger.info(f"Granted permission '{permission}' to user {user_id}")
            return True

        return False

    def revoke_permission(
        self,
        user_id: str,
        permission: str,
        admin_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Revoke permission from user"""
        if user_id in self.user_permissions:
            if permission in self.user_permissions[user_id]:
                self.user_permissions[user_id].remove(permission)

                # Record audit
                audit = UserPermissionAudit(
                    user_id=user_id,
                    admin_id=admin_id,
                    action="revoke",
                    permission=permission,
                    reason=reason,
                )
                self.audit_logs.append(audit)

                logger.info(f"Revoked permission '{permission}' from user {user_id}")
                return True

        return False

    def get_permission_audit_log(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get permission change audit log"""
        logs = self.audit_logs

        if user_id:
            logs = [log for log in logs if log.user_id == user_id]

        # Sort by creation time (newest first)
        logs.sort(key=lambda log: log.created_at, reverse=True)

        return [log.to_dict() for log in logs[:limit]]

    def get_user_activity_summary(self) -> Dict[str, Any]:
        """Get user activity summary"""
        if not self.users:
            return {
                "total_users": 0,
                "active_users": 0,
                "inactive_users": 0,
                "last_24h_logins": 0,
                "last_30d_logins": 0,
            }

        active_users = sum(1 for u in self.users.values() if u.is_active)
        inactive_users = len(self.users) - active_users

        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_30d = now - timedelta(days=30)

        last_24h_logins = sum(
            1
            for u in self.users.values()
            if u.last_login and u.last_login > last_24h
        )
        last_30d_logins = sum(
            1
            for u in self.users.values()
            if u.last_login and u.last_login > last_30d
        )

        return {
            "total_users": len(self.users),
            "active_users": active_users,
            "inactive_users": inactive_users,
            "last_24h_logins": last_24h_logins,
            "last_30d_logins": last_30d_logins,
            "total_permission_changes": len(self.audit_logs),
        }

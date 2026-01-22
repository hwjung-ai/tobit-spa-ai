"""Admin dashboard settings management service"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SettingAudit:
    """Track setting changes"""

    def __init__(
        self,
        setting_key: str,
        old_value: Any,
        new_value: Any,
        admin_id: str,
        reason: Optional[str] = None,
    ):
        self.setting_key = setting_key
        self.old_value = old_value
        self.new_value = new_value
        self.admin_id = admin_id
        self.reason = reason
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "setting_key": self.setting_key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "admin_id": self.admin_id,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


class AdminSettingsService:
    """Manage system-wide settings"""

    def __init__(self):
        self.settings: Dict[str, Any] = self._default_settings()
        self.audit_logs: List[SettingAudit] = []

    def _default_settings(self) -> Dict[str, Any]:
        """Get default settings"""
        return {
            # API settings
            "api_rate_limit_enabled": True,
            "api_rate_limit_requests_per_minute": 1000,
            "api_request_timeout_seconds": 30,
            "api_max_payload_size_mb": 50,

            # Document processing
            "document_processing_max_file_size_mb": 500,
            "document_processing_timeout_seconds": 300,
            "document_ocr_enabled": True,
            "document_enable_async_processing": True,

            # Database
            "database_connection_pool_size": 20,
            "database_query_timeout_seconds": 60,
            "database_slow_query_threshold_ms": 1000,
            "database_enable_query_logging": True,

            # CEP Engine
            "cep_max_rule_executions_per_minute": 10000,
            "cep_notification_retry_count": 3,
            "cep_enable_performance_monitoring": True,

            # Chat Enhancement
            "chat_auto_title_enabled": True,
            "chat_token_tracking_enabled": True,
            "chat_max_history_days": 90,
            "chat_enable_search": True,

            # Security
            "security_password_min_length": 12,
            "security_password_require_special_char": True,
            "security_password_require_numbers": True,
            "security_session_timeout_minutes": 60,
            "security_mfa_enabled": True,
            "security_enable_audit_logging": True,

            # Notifications
            "notifications_slack_enabled": True,
            "notifications_email_enabled": True,
            "notifications_sms_enabled": False,
            "notifications_max_retries": 3,

            # Monitoring
            "monitoring_metrics_retention_days": 30,
            "monitoring_alert_threshold_cpu_percent": 85,
            "monitoring_alert_threshold_memory_percent": 85,
            "monitoring_alert_threshold_disk_percent": 90,

            # Maintenance
            "maintenance_backup_enabled": True,
            "maintenance_backup_frequency_hours": 24,
            "maintenance_log_retention_days": 30,
        }

    def get_setting(self, key: str) -> Optional[Any]:
        """Get a single setting"""
        return self.settings.get(key)

    def get_settings(self, keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get multiple settings or all if no keys specified"""
        if keys is None:
            return self.settings.copy()

        return {k: self.settings.get(k) for k in keys if k in self.settings}

    def update_setting(
        self,
        key: str,
        value: Any,
        admin_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Update a setting"""

        if key not in self.settings:
            logger.warning(f"Unknown setting key: {key}")
            return False

        old_value = self.settings[key]

        # Validate setting value
        if not self._validate_setting(key, value):
            logger.error(f"Invalid value for setting {key}: {value}")
            return False

        # Update setting
        self.settings[key] = value

        # Record audit
        audit = SettingAudit(
            setting_key=key,
            old_value=old_value,
            new_value=value,
            admin_id=admin_id,
            reason=reason,
        )
        self.audit_logs.append(audit)

        logger.info(f"Updated setting {key}: {old_value} -> {value}")

        return True

    def update_settings_batch(
        self,
        updates: Dict[str, Any],
        admin_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Update multiple settings"""
        results = {}

        for key, value in updates.items():
            results[key] = self.update_setting(key, value, admin_id, reason)

        return results

    def _validate_setting(self, key: str, value: Any) -> bool:
        """Validate setting value"""

        # Type checks
        if "enabled" in key or key.startswith("enable_"):
            if not isinstance(value, bool):
                return False

        elif "seconds" in key or "minutes" in key or "hours" in key or "days" in key:
            if not isinstance(value, int) or value <= 0:
                return False

        elif "percent" in key:
            if not isinstance(value, (int, float)) or not (0 <= value <= 100):
                return False

        elif "size_mb" in key:
            if not isinstance(value, (int, float)) or value <= 0:
                return False

        elif "min_length" in key:
            if not isinstance(value, int) or value < 1:
                return False

        # Range checks for specific settings
        if key == "api_rate_limit_requests_per_minute":
            if value < 100 or value > 1000000:
                return False

        elif key == "api_request_timeout_seconds":
            if value < 1 or value > 300:
                return False

        return True

    def get_settings_audit_log(
        self,
        key: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get settings change audit log"""
        logs = self.audit_logs

        if key:
            logs = [log for log in logs if log.setting_key == key]

        # Sort by creation time (newest first)
        logs.sort(key=lambda log: log.created_at, reverse=True)

        return [log.to_dict() for log in logs[:limit]]

    def reset_to_defaults(self, admin_id: str, reason: Optional[str] = None) -> int:
        """Reset all settings to defaults"""
        default_settings = self._default_settings()
        count = 0

        for key, default_value in default_settings.items():
            if self.settings.get(key) != default_value:
                self.update_setting(key, default_value, admin_id, reason or "Reset to defaults")
                count += 1

        logger.info(f"Reset {count} settings to defaults")

        return count

    def export_settings(self) -> Dict[str, Any]:
        """Export all settings"""
        return {
            "settings": self.settings.copy(),
            "exported_at": datetime.utcnow().isoformat(),
        }

    def import_settings(
        self,
        settings: Dict[str, Any],
        admin_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Import settings from export"""
        results = {}

        for key, value in settings.items():
            if key in self.settings:
                results[key] = self.update_setting(key, value, admin_id, reason or "Imported from backup")
            else:
                logger.warning(f"Unknown setting in import: {key}")
                results[key] = False

        return results

    def get_settings_by_category(self) -> Dict[str, Dict[str, Any]]:
        """Get settings grouped by category"""
        categories = {
            "api": {},
            "document": {},
            "database": {},
            "cep": {},
            "chat": {},
            "security": {},
            "notifications": {},
            "monitoring": {},
            "maintenance": {},
        }

        for key, value in self.settings.items():
            for category in categories:
                if key.startswith(category):
                    categories[category][key] = value
                    break

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

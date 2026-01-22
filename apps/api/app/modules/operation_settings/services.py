from __future__ import annotations

from typing import Any

from core.config import AppSettings
from sqlmodel import Session

from app.modules.operation_settings.crud import (
    create_or_update_setting,
    get_setting_effective_value,
)


class OperationSettingsService:
    """Service for managing operation settings with priority resolution."""

    # Settings that can be changed at runtime
    CONFIGURABLE_SETTINGS = {
        "ops_mode": {
            "type": str,
            "default": "mock",
            "allowed_values": ["mock", "real"],
            "restart_required": True,
            "description": "Operation mode: mock or real",
        },
        "ops_enable_langgraph": {
            "type": bool,
            "default": False,
            "restart_required": True,
            "description": "Enable LangGraph for OPS ALL executor",
        },
        "enable_system_apis": {
            "type": bool,
            "default": False,
            "restart_required": False,
            "description": "Enable system APIs",
        },
        "enable_data_explorer": {
            "type": bool,
            "default": False,
            "restart_required": False,
            "description": "Enable data explorer",
        },
        "cep_enable_metric_polling": {
            "type": bool,
            "default": False,
            "restart_required": True,
            "description": "Enable CEP metric polling",
        },
        "cep_metric_poll_global_interval_seconds": {
            "type": int,
            "default": 10,
            "restart_required": True,
            "description": "CEP metric polling global interval in seconds",
        },
        "cep_metric_poll_concurrency": {
            "type": int,
            "default": 5,
            "restart_required": True,
            "description": "CEP metric polling concurrency",
        },
        "cep_enable_notifications": {
            "type": bool,
            "default": False,
            "restart_required": False,
            "description": "Enable CEP notifications",
        },
        "cep_enable_cep_scheduler": {
            "type": bool,
            "default": False,
            "restart_required": True,
            "description": "Enable CEP scheduler",
        },
    }

    @staticmethod
    def get_all_settings(
        session: Session,
        current_app_settings: AppSettings,
    ) -> dict[str, dict[str, Any]]:
        """
        Get all settings with effective values and sources.

        Returns a dict mapping setting_key to:
        {
            "value": effective_value,
            "source": "published" | "env" | "default",
            "restart_required": bool,
            "description": str,
            "default": default_value,
            "allowed_values": list or None,
        }
        """
        result = {}

        # Get environment variable values
        env_values = {
            "ops_mode": current_app_settings.ops_mode,
            "ops_enable_langgraph": current_app_settings.ops_enable_langgraph,
            "enable_system_apis": current_app_settings.enable_system_apis,
            "enable_data_explorer": current_app_settings.enable_data_explorer,
            "cep_enable_metric_polling": current_app_settings.cep_enable_metric_polling,
            "cep_metric_poll_global_interval_seconds": current_app_settings.cep_metric_poll_global_interval_seconds,
            "cep_metric_poll_concurrency": current_app_settings.cep_metric_poll_concurrency,
            "cep_enable_notifications": current_app_settings.cep_enable_notifications,
            "cep_enable_cep_scheduler": current_app_settings.ops_enable_cep_scheduler,
        }

        for setting_key, config in OperationSettingsService.CONFIGURABLE_SETTINGS.items():
            env_value = env_values.get(setting_key)
            effective = get_setting_effective_value(
                session,
                setting_key,
                default_value=config["default"],
                env_value=env_value,
            )

            result[setting_key] = {
                "value": effective["value"],
                "source": effective["source"],
                "restart_required": effective["restart_required"],
                "description": config["description"],
                "default": config["default"],
                "allowed_values": config.get("allowed_values"),
            }

        return result

    @staticmethod
    def get_setting(
        session: Session,
        setting_key: str,
        current_app_settings: AppSettings,
    ) -> dict[str, Any]:
        """Get a single setting with effective value and source."""
        if setting_key not in OperationSettingsService.CONFIGURABLE_SETTINGS:
            raise ValueError(f"Unknown setting: {setting_key}")

        config = OperationSettingsService.CONFIGURABLE_SETTINGS[setting_key]

        # Get environment variable value
        env_values = {
            "ops_mode": current_app_settings.ops_mode,
            "ops_enable_langgraph": current_app_settings.ops_enable_langgraph,
            "enable_system_apis": current_app_settings.enable_system_apis,
            "enable_data_explorer": current_app_settings.enable_data_explorer,
            "cep_enable_metric_polling": current_app_settings.cep_enable_metric_polling,
            "cep_metric_poll_global_interval_seconds": current_app_settings.cep_metric_poll_global_interval_seconds,
            "cep_metric_poll_concurrency": current_app_settings.cep_metric_poll_concurrency,
            "cep_enable_notifications": current_app_settings.cep_enable_notifications,
            "cep_enable_cep_scheduler": current_app_settings.ops_enable_cep_scheduler,
        }

        env_value = env_values.get(setting_key)
        effective = get_setting_effective_value(
            session,
            setting_key,
            default_value=config["default"],
            env_value=env_value,
        )

        return {
            "key": setting_key,
            "value": effective["value"],
            "source": effective["source"],
            "restart_required": effective["restart_required"],
            "description": config["description"],
            "default": config["default"],
            "allowed_values": config.get("allowed_values"),
        }

    @staticmethod
    def update_setting(
        session: Session,
        setting_key: str,
        new_value: Any,
        updated_by: str = "admin",
    ) -> dict[str, Any]:
        """
        Update a setting.

        Args:
            session: Database session
            setting_key: The setting key to update
            new_value: The new value
            updated_by: Who is making the change

        Returns:
            The updated setting with metadata

        Raises:
            ValueError: If setting is unknown or value is invalid
        """
        if setting_key not in OperationSettingsService.CONFIGURABLE_SETTINGS:
            raise ValueError(f"Unknown setting: {setting_key}")

        config = OperationSettingsService.CONFIGURABLE_SETTINGS[setting_key]

        # Validate value type
        expected_type = config["type"]
        if not isinstance(new_value, expected_type):
            raise ValueError(
                f"Invalid type for {setting_key}: expected {expected_type.__name__}, got {type(new_value).__name__}"
            )

        # Validate against allowed values if defined
        if "allowed_values" in config and new_value not in config["allowed_values"]:
            raise ValueError(
                f"Invalid value for {setting_key}: {new_value}. Allowed values: {config['allowed_values']}"
            )

        # Create or update the setting
        setting = create_or_update_setting(
            session=session,
            setting_key=setting_key,
            setting_value={"value": new_value},
            description=config["description"],
            published_by=updated_by,
            restart_required=config["restart_required"],
        )

        return {
            "key": setting_key,
            "value": new_value,
            "source": "published",
            "restart_required": setting.restart_required,
            "description": config["description"],
            "published_by": updated_by,
            "published_at": setting.published_at.isoformat() if setting.published_at else None,
        }

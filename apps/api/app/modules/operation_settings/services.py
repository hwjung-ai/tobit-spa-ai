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
        "log_level": {
            "type": str,
            "default": "info",
            "allowed_values": ["debug", "info", "warning", "error"],
            "restart_required": True,
            "description": "Logging level for application",
        },
        "log_retention_days": {
            "type": int,
            "default": 30,
            "restart_required": False,
            "description": "Number of days to retain log files",
        },
        "log_max_file_size_mb": {
            "type": int,
            "default": 100,
            "restart_required": False,
            "description": "Maximum log file size in megabytes before rotation",
        },
        "log_enable_file_rotation": {
            "type": bool,
            "default": True,
            "restart_required": False,
            "description": "Enable automatic log file rotation",
        },
        "log_enable_json_format": {
            "type": bool,
            "default": False,
            "restart_required": True,
            "description": "Enable JSON format for log output",
        },
        "log_console_output": {
            "type": bool,
            "default": True,
            "restart_required": True,
            "description": "Enable console output for logs",
        },
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
        "llm_provider": {
            "type": str,
            "default": "openai",
            "allowed_values": ["openai", "internal"],
            "restart_required": True,
            "description": "Primary LLM provider",
        },
        "llm_base_url": {
            "type": str,
            "default": "",
            "restart_required": True,
            "description": "Base URL for internal/OpenAI-compatible LLM endpoint",
        },
        "llm_default_model": {
            "type": str,
            "default": "gpt-5-nano",
            "restart_required": True,
            "description": "Default chat model used by LLM gateway",
        },
        "llm_fallback_model": {
            "type": str,
            "default": "",
            "restart_required": True,
            "description": "Fallback model when primary model call fails",
        },
        "llm_timeout_seconds": {
            "type": int,
            "default": 120,
            "restart_required": False,
            "description": "LLM request timeout in seconds",
        },
        "llm_max_retries": {
            "type": int,
            "default": 2,
            "restart_required": False,
            "description": "Maximum retries for transient LLM failures",
        },
        "llm_enable_fallback": {
            "type": bool,
            "default": True,
            "restart_required": False,
            "description": "Enable automatic fallback model routing",
        },
        "llm_routing_policy": {
            "type": str,
            "default": "default",
            "allowed_values": ["default", "latency", "cost", "quality"],
            "restart_required": False,
            "description": "Routing policy profile for model selection",
        },
        "api_auth_default_mode": {
            "type": str,
            "default": "jwt_only",
            "allowed_values": ["jwt_only", "jwt_or_api_key", "api_key_only"],
            "restart_required": False,
            "description": "Default auth mode for runtime APIs when API-level mode is not set",
        },
        "api_auth_enforce_scopes": {
            "type": bool,
            "default": True,
            "restart_required": False,
            "description": "When true, API key scopes must satisfy runtime API required scopes",
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
            "log_level": current_app_settings.log_level,
            "log_retention_days": current_app_settings.log_retention_days,
            "log_max_file_size_mb": current_app_settings.log_max_file_size_mb,
            "log_enable_file_rotation": current_app_settings.log_enable_file_rotation,
            "log_enable_json_format": current_app_settings.log_enable_json_format,
            "log_console_output": current_app_settings.log_console_output,
            "ops_mode": current_app_settings.ops_mode,
            "ops_enable_langgraph": current_app_settings.ops_enable_langgraph,
            "enable_system_apis": current_app_settings.enable_system_apis,
            "enable_data_explorer": current_app_settings.enable_data_explorer,
            "cep_enable_metric_polling": current_app_settings.cep_enable_metric_polling,
            "cep_metric_poll_global_interval_seconds": current_app_settings.cep_metric_poll_global_interval_seconds,
            "cep_metric_poll_concurrency": current_app_settings.cep_metric_poll_concurrency,
            "cep_enable_notifications": current_app_settings.cep_enable_notifications,
            "cep_enable_cep_scheduler": current_app_settings.ops_enable_cep_scheduler,
            "llm_provider": current_app_settings.llm_provider,
            "llm_base_url": current_app_settings.llm_base_url or "",
            "llm_default_model": current_app_settings.llm_default_model
            or current_app_settings.chat_model,
            "llm_fallback_model": current_app_settings.llm_fallback_model or "",
            "llm_timeout_seconds": current_app_settings.llm_timeout_seconds,
            "llm_max_retries": current_app_settings.llm_max_retries,
            "llm_enable_fallback": current_app_settings.llm_enable_fallback,
            "llm_routing_policy": current_app_settings.llm_routing_policy,
            "api_auth_default_mode": current_app_settings.api_auth_default_mode,
            "api_auth_enforce_scopes": current_app_settings.api_auth_enforce_scopes,
        }

        for (
            setting_key,
            config,
        ) in OperationSettingsService.CONFIGURABLE_SETTINGS.items():
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
            "log_level": current_app_settings.log_level,
            "log_retention_days": current_app_settings.log_retention_days,
            "log_max_file_size_mb": current_app_settings.log_max_file_size_mb,
            "log_enable_file_rotation": current_app_settings.log_enable_file_rotation,
            "log_enable_json_format": current_app_settings.log_enable_json_format,
            "log_console_output": current_app_settings.log_console_output,
            "ops_mode": current_app_settings.ops_mode,
            "ops_enable_langgraph": current_app_settings.ops_enable_langgraph,
            "enable_system_apis": current_app_settings.enable_system_apis,
            "enable_data_explorer": current_app_settings.enable_data_explorer,
            "cep_enable_metric_polling": current_app_settings.cep_enable_metric_polling,
            "cep_metric_poll_global_interval_seconds": current_app_settings.cep_metric_poll_global_interval_seconds,
            "cep_metric_poll_concurrency": current_app_settings.cep_metric_poll_concurrency,
            "cep_enable_notifications": current_app_settings.cep_enable_notifications,
            "cep_enable_cep_scheduler": current_app_settings.ops_enable_cep_scheduler,
            "llm_provider": current_app_settings.llm_provider,
            "llm_base_url": current_app_settings.llm_base_url or "",
            "llm_default_model": current_app_settings.llm_default_model
            or current_app_settings.chat_model,
            "llm_fallback_model": current_app_settings.llm_fallback_model or "",
            "llm_timeout_seconds": current_app_settings.llm_timeout_seconds,
            "llm_max_retries": current_app_settings.llm_max_retries,
            "llm_enable_fallback": current_app_settings.llm_enable_fallback,
            "llm_routing_policy": current_app_settings.llm_routing_policy,
            "api_auth_default_mode": current_app_settings.api_auth_default_mode,
            "api_auth_enforce_scopes": current_app_settings.api_auth_enforce_scopes,
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
            "published_at": setting.published_at.isoformat()
            if setting.published_at
            else None,
        }

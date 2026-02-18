"""Unit tests for tool option operation settings."""

import pytest
from app.modules.operation_settings.services import OperationSettingsService
from core.config import get_settings


def test_get_all_settings_includes_tool_option_keys(session):
    settings = OperationSettingsService.get_all_settings(session, get_settings())
    assert "ops_tool_capabilities" in settings
    assert "ops_tool_supported_modes" in settings
    assert isinstance(settings["ops_tool_capabilities"]["value"], list)
    assert isinstance(settings["ops_tool_supported_modes"]["value"], list)


def test_update_tool_capabilities_setting_accepts_string_list(session):
    updated = OperationSettingsService.update_setting(
        session=session,
        setting_key="ops_tool_capabilities",
        new_value=["ci_lookup", "custom_capability"],
        updated_by="test_user",
    )
    assert updated["key"] == "ops_tool_capabilities"
    assert updated["value"] == ["ci_lookup", "custom_capability"]


def test_update_tool_supported_modes_setting_rejects_non_string_list_item(session):
    with pytest.raises(
        ValueError,
        match="list must contain non-empty strings only",
    ):
        OperationSettingsService.update_setting(
            session=session,
            setting_key="ops_tool_supported_modes",
            new_value=["config", 1],
            updated_by="test_user",
        )

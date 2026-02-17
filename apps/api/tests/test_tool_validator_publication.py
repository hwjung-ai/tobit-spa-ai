from __future__ import annotations

from types import SimpleNamespace

from app.modules.asset_registry.tool_validator import validate_tool_for_publication


def test_publication_validation_does_not_fail_for_missing_source_tag() -> None:
    asset = SimpleNamespace(
        tool_type="database_query",
        tool_config={"source_ref": "default_postgres", "query_template": "SELECT 1"},
        tool_input_schema={"type": "object", "properties": {}},
        tool_output_schema=None,
        name="sample_tool",
        tool_catalog_ref=None,
        description="tool for publication",
        tags={},
    )

    errors = validate_tool_for_publication(asset)
    assert "Tool tags with 'source' are recommended for publication" not in errors

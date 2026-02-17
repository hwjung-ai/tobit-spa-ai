from __future__ import annotations

from types import SimpleNamespace

from app.modules.asset_registry import tool_router


def test_validate_tool_references_fails_when_source_missing(monkeypatch) -> None:
    def fake_resolve(*_args, **kwargs):
        if kwargs.get("asset_type") == "source":
            return None
        return None

    monkeypatch.setattr(tool_router, "_resolve_published_asset_by_ref", fake_resolve)

    errors = tool_router._validate_tool_references(
        session=SimpleNamespace(),
        tool_type="database_query",
        tool_config={"source_ref": "missing_source", "query_template": "SELECT 1"},
        tool_catalog_ref=None,
        tenant_id="tenant-a",
    )

    assert any("source_ref 'missing_source' not found" in err for err in errors)


def test_validate_tool_references_fails_when_catalog_source_mismatch(monkeypatch) -> None:
    source_asset = SimpleNamespace(name="source_a", content={})
    catalog_asset = SimpleNamespace(
        name="catalog_b",
        content={"catalog": {"source_ref": "source_b"}},
    )

    def fake_resolve(*_args, **kwargs):
        if kwargs.get("asset_type") == "source":
            return source_asset
        if kwargs.get("asset_type") == "catalog":
            return catalog_asset
        return None

    monkeypatch.setattr(tool_router, "_resolve_published_asset_by_ref", fake_resolve)

    errors = tool_router._validate_tool_references(
        session=SimpleNamespace(),
        tool_type="database_query",
        tool_config={"source_ref": "source_a", "query_template": "SELECT 1"},
        tool_catalog_ref="catalog_b",
        tenant_id="tenant-a",
    )

    assert any("tool_catalog_ref source mismatch" in err for err in errors)


def test_validate_tool_references_accepts_matching_source_and_catalog(monkeypatch) -> None:
    source_asset = SimpleNamespace(name="source_a", content={})
    catalog_asset = SimpleNamespace(
        name="catalog_a",
        content={"catalog": {"source_ref": "source_a"}},
    )

    def fake_resolve(*_args, **kwargs):
        if kwargs.get("asset_type") == "source":
            return source_asset
        if kwargs.get("asset_type") == "catalog":
            return catalog_asset
        return None

    monkeypatch.setattr(tool_router, "_resolve_published_asset_by_ref", fake_resolve)

    errors = tool_router._validate_tool_references(
        session=SimpleNamespace(),
        tool_type="database_query",
        tool_config={"source_ref": "source_a", "query_template": "SELECT 1"},
        tool_catalog_ref="catalog_a",
        tenant_id="tenant-a",
    )

    assert errors == []

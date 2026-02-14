from __future__ import annotations

from app.modules.inspector.service import _build_applied_assets, _compute_fallbacks


def test_build_applied_assets_maps_schema_to_catalog() -> None:
    state = {
        "schema": {
            "asset_id": "catalog-asset-1",
            "name": "main_catalog",
            "version": 3,
            "source": "asset_registry",
        }
    }

    applied_assets = _build_applied_assets(state)

    assert applied_assets["catalog"] is not None
    assert applied_assets["catalog"]["asset_id"] == "catalog-asset-1"
    assert applied_assets["catalog"]["name"] == "main_catalog"
    # Backward compatibility
    assert applied_assets["schema"] == applied_assets["catalog"]


def test_compute_fallbacks_maps_schema_to_catalog() -> None:
    state = {
        "schema": {
            "asset_id": "catalog-asset-1",
            "name": "main_catalog",
            "version": 3,
            "source": "asset_registry",
        }
    }

    fallbacks = _compute_fallbacks(state)

    assert fallbacks["catalog"] is False
    # Backward compatibility
    assert fallbacks["schema"] == fallbacks["catalog"]

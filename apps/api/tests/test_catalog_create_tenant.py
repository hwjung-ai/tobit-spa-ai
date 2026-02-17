from __future__ import annotations

import importlib
from datetime import datetime
from types import SimpleNamespace

from app.modules.auth.models import TbUser, UserRole
from core.auth import get_current_user
from fastapi.testclient import TestClient
from main import app


def _debug_user() -> TbUser:
    return TbUser(
        id="dev-user",
        username="debug@dev",
        password_hash="",
        role=UserRole.ADMIN,
        tenant_id="default",
        is_active=True,
    )


def test_create_catalog_passes_tenant_id_to_crud(monkeypatch) -> None:
    asset_router = importlib.import_module("app.modules.asset_registry.router")

    captured: dict[str, object] = {}

    def _fake_create_schema_asset(session, payload, tenant_id=None, created_by=None):  # noqa: ANN001
        captured["tenant_id"] = tenant_id
        captured["created_by"] = created_by
        captured["payload_source_ref"] = payload.source_ref
        return SimpleNamespace(
            asset_id="11111111-1111-4111-8111-111111111111",
            asset_type="catalog",
            name=payload.name,
            description=payload.description,
            version=1,
            status="draft",
            catalog={"name": payload.name, "source_ref": payload.source_ref, "tables": []},
            scope=None,
            tags={},
            created_by=created_by,
            published_by=None,
            published_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    monkeypatch.setattr(asset_router, "create_schema_asset", _fake_create_schema_asset)
    app.dependency_overrides[get_current_user] = _debug_user

    try:
        client = TestClient(app)
        response = client.post(
            "/asset-registry/catalogs",
            json={
                "name": "catalog_tenant_regression",
                "description": "tenant propagation regression test",
                "source_ref": "source_test_default",
            },
            headers={"X-Tenant-Id": "default"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "tenant_id": "default",
        "created_by": "dev-user",
        "payload_source_ref": "source_test_default",
    }

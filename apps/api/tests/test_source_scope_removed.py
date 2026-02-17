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


def test_create_source_ignores_scope_and_response_omits_scope(monkeypatch) -> None:
    asset_router = importlib.import_module("app.modules.asset_registry.router")

    captured: dict[str, object] = {}

    def _fake_create_source_asset(session, payload, tenant_id=None, created_by=None):  # noqa: ANN001
        captured["tenant_id"] = tenant_id
        captured["created_by"] = created_by
        captured["has_scope_field"] = hasattr(payload, "scope")
        return SimpleNamespace(
            asset_id="11111111-1111-4111-8111-111111111111",
            asset_type="source",
            name=payload.name,
            description=payload.description,
            version=1,
            status="draft",
            source_type=payload.source_type,
            connection=payload.connection,
            tags={},
            created_by=created_by,
            published_by=None,
            published_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    monkeypatch.setattr(asset_router, "create_source_asset", _fake_create_source_asset)
    app.dependency_overrides[get_current_user] = _debug_user

    try:
        client = TestClient(app)
        response = client.post(
            "/asset-registry/sources",
            json={
                "name": "source_without_scope",
                "description": "scope removal regression test",
                "source_type": "postgresql",
                "scope": "ops",
                "connection": {
                    "host": "localhost",
                    "port": 5432,
                    "username": "admin",
                    "database": "spadb",
                    "timeout": 30,
                },
            },
            headers={"X-Tenant-Id": "default"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert "scope" not in data
    assert captured == {
        "tenant_id": "default",
        "created_by": "dev-user",
        "has_scope_field": False,
    }


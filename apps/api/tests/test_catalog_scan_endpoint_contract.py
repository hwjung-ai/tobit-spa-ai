from __future__ import annotations

import importlib
from contextlib import contextmanager
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


def test_catalog_scan_accepts_object_payload(monkeypatch) -> None:
    asset_router = importlib.import_module("app.modules.asset_registry.router")
    asset_crud = importlib.import_module("app.modules.asset_registry.crud")

    catalog_id = "11111111-1111-4111-8111-111111111111"
    scanned_args: dict[str, object] = {}
    fake_asset = SimpleNamespace(
        asset_id=catalog_id,
        asset_type="catalog",
        name="Catalog One",
        status="draft",
        content={},
    )
    fake_updated = SimpleNamespace(
        asset_id=catalog_id,
        name="Catalog One",
        status="draft",
        content={"catalog": {"scan_status": "completed"}},
    )

    class _FakeSession:
        def get(self, model, asset_id: str):  # noqa: ANN001
            if asset_id == catalog_id:
                return fake_asset
            return None

    @contextmanager
    def _fake_session_context():
        yield _FakeSession()

    async def _fake_scan_schema_asset(session, asset, schema_names, include_row_counts):  # noqa: ANN001
        scanned_args["schema_names"] = schema_names
        scanned_args["include_row_counts"] = include_row_counts
        return fake_updated

    monkeypatch.setattr(asset_router, "get_session_context", _fake_session_context)
    monkeypatch.setattr(asset_crud, "scan_schema_asset", _fake_scan_schema_asset)
    app.dependency_overrides[get_current_user] = _debug_user

    try:
        client = TestClient(app)
        response = client.post(
            f"/asset-registry/catalogs/{catalog_id}/scan",
            json={"schema_names": ["public"], "include_row_counts": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["asset_id"] == catalog_id
    assert scanned_args == {
        "schema_names": ["public"],
        "include_row_counts": False,
    }


def test_catalog_scan_rejects_invalid_asset_id_format() -> None:
    app.dependency_overrides[get_current_user] = _debug_user

    try:
        client = TestClient(app)
        response = client.post(
            "/asset-registry/catalogs/not-a-uuid/scan",
            json={"schema_names": ["public"], "include_row_counts": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"] == "Invalid catalog asset_id format"

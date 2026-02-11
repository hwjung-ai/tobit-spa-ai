from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.modules.api_keys.crud import create_api_key
from app.modules.api_manager import runtime_router as runtime_router_module
from app.modules.auth.models import TbUser, UserRole
from core.auth import get_settings as auth_get_settings
from main import app
from models.api_definition import ApiAuthMode, ApiDefinition, ApiMode, ApiScope


@pytest.fixture
def client_with_auth(session, monkeypatch):
    def get_session_override():
        yield session

    settings = SimpleNamespace(
        enable_auth=True,
        jwt_secret_key="test-secret",
        jwt_algorithm="HS256",
        api_auth_default_mode="jwt_only",
        api_auth_enforce_scopes=True,
    )
    monkeypatch.setattr("core.auth.get_settings", lambda: settings)
    monkeypatch.setattr(
        "core.auth._resolve_runtime_api_policy",
        lambda session, request, settings: ("api_key_only", ["api:execute"], True),
    )
    monkeypatch.setattr(
        runtime_router_module,
        "execute_sql_api",
        lambda **kwargs: SimpleNamespace(
            columns=["value"],
            rows=[[1]],
            row_count=1,
            duration_ms=1,
            params={},
        ),
    )

    import core.db

    app.dependency_overrides[core.db.get_session] = get_session_override
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        monkeypatch.setattr("core.auth.get_settings", auth_get_settings)


def _create_user(session, user_id: str = "u-runtime") -> TbUser:
    user = TbUser(
        id=user_id,
        username=f"{user_id}@example.com",
        password_hash="x",
        role=UserRole.ADMIN,
        tenant_id="t1",
        is_active=True,
        email_encrypted=f"{user_id}@example.com",
        phone_encrypted=None,
    )
    session.add(user)
    session.commit()
    return user


def _create_runtime_api(
    session,
    *,
    path: str,
    auth_mode: ApiAuthMode,
    required_scopes: list[str] | None = None,
) -> ApiDefinition:
    api = ApiDefinition(
        scope=ApiScope.custom,
        name=f"runtime-{path.strip('/').replace('/', '-')}",
        method="GET",
        path=path,
        mode=ApiMode.sql,
        logic="SELECT 1 as value",
        auth_mode=auth_mode,
        required_scopes=required_scopes or [],
        is_enabled=True,
    )
    session.add(api)
    session.commit()
    session.refresh(api)
    return api


def test_runtime_api_key_only_accepts_registered_key(client_with_auth):
    client, session = client_with_auth
    user = _create_user(session, "u-api-key")
    _create_runtime_api(
        session,
        path="/runtime/hybrid-demo",
        auth_mode=ApiAuthMode.api_key_only,
        required_scopes=["api:execute"],
    )
    _, full_key = create_api_key(
        session=session,
        user_id=user.id,
        name="runtime-test-key",
        scope=["api:execute"],
    )

    response = client.get(
        "/runtime/hybrid-demo",
        headers={"Authorization": f"Bearer {full_key}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["result"]["row_count"] == 1


def test_runtime_api_key_only_rejects_missing_scope(client_with_auth):
    client, session = client_with_auth
    user = _create_user(session, "u-scope-miss")
    _create_runtime_api(
        session,
        path="/runtime/hybrid-scope",
        auth_mode=ApiAuthMode.api_key_only,
        required_scopes=["api:execute"],
    )
    _, full_key = create_api_key(
        session=session,
        user_id=user.id,
        name="runtime-missing-scope",
        scope=["api:read"],
    )

    response = client.get(
        "/runtime/hybrid-scope",
        headers={"Authorization": f"Bearer {full_key}"},
    )
    assert response.status_code == 403

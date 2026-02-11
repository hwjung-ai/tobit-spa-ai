from __future__ import annotations

from app.modules.auth.models import TbUser, UserRole
from core.auth import get_current_user
from fastapi.testclient import TestClient
from main import app


def _mock_user(tenant_id: str = "t1") -> TbUser:
    return TbUser(
        username="sim-user",
        password_hash="hashed",
        role=UserRole.ADMIN,
        tenant_id=tenant_id,
        is_active=True,
        email_encrypted="enc-email",
        phone_encrypted=None,
    )


def test_query_rejects_tenant_mismatch():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("t1")
    client = TestClient(app)

    response = client.post(
        "/sim/query",
        json={
            "question": "tenant mismatch",
            "scenario_type": "what_if",
            "strategy": "rule",
            "horizon": "7d",
            "service": "api-gateway",
            "assumptions": {"traffic_change_pct": 10},
        },
        headers={"X-Tenant-Id": "t2"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403

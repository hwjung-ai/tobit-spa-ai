from __future__ import annotations

from app.modules.auth.models import TbUser, UserRole
from core.auth import get_current_user
from core.db import get_session
from core.tenant import get_current_tenant
from fastapi.testclient import TestClient
from main import app
from models.chat import ChatThread


def _make_user(user_id: str, tenant_id: str) -> TbUser:
    return TbUser(
        id=user_id,
        username=f"{user_id}@test.local",
        password_hash="",
        role=UserRole.ADMIN,
        tenant_id=tenant_id,
        is_active=True,
        email_encrypted="",
    )


def test_threads_list_and_get_are_scoped_by_identity(session):
    state = {"user": _make_user("u1", "t1"), "tenant": "t1"}

    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    app.dependency_overrides[get_current_user] = lambda: state["user"]
    app.dependency_overrides[get_current_tenant] = lambda: state["tenant"]

    own_thread = ChatThread(title="mine", tenant_id="t1", user_id="u1", builder=None)
    other_thread = ChatThread(
        title="other", tenant_id="t1", user_id="u2", builder=None
    )
    session.add(own_thread)
    session.add(other_thread)
    session.commit()
    session.refresh(own_thread)
    session.refresh(other_thread)

    client = TestClient(app)

    list_response = client.get("/threads/")
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == own_thread.id

    own_response = client.get(f"/threads/{own_thread.id}")
    assert own_response.status_code == 200

    blocked_response = client.get(f"/threads/{other_thread.id}")
    assert blocked_response.status_code == 404

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_tenant, None)

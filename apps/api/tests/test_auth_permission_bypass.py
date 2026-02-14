from types import SimpleNamespace

import pytest
from app.modules.auth.models import UserRole
from core.auth import require_role
from fastapi import HTTPException


def test_require_role_enforced_by_default(monkeypatch):
    monkeypatch.setattr(
        "core.auth.get_settings",
        lambda: SimpleNamespace(enable_permission_check=True),
    )
    checker = require_role(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=SimpleNamespace(role=UserRole.VIEWER))
    assert exc_info.value.status_code == 403


def test_require_role_bypassed_when_permission_check_disabled(monkeypatch):
    monkeypatch.setattr(
        "core.auth.get_settings",
        lambda: SimpleNamespace(enable_permission_check=False),
    )
    checker = require_role(UserRole.ADMIN)
    user = SimpleNamespace(role=UserRole.VIEWER)
    assert checker(current_user=user) is user

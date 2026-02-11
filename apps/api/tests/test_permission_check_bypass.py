from types import SimpleNamespace

from app.modules.auth.models import UserRole
from app.modules.permissions.crud import check_permission
from app.modules.permissions.models import ResourcePermission


def test_check_permission_bypassed_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.modules.permissions.crud.get_settings",
        lambda: SimpleNamespace(enable_permission_check=False),
    )
    result = check_permission(
        session=None,  # bypass happens before any DB access
        user_id="u-dev",
        role=UserRole.VIEWER,
        permission=ResourcePermission.API_DELETE,
    )
    assert result.granted is True

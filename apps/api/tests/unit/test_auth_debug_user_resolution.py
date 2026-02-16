from app.modules.auth.models import TbUser, UserRole
from core.auth import _pick_debug_user


def _user(user_id: str, username: str, role: UserRole, active: bool = True) -> TbUser:
    return TbUser(
        id=user_id,
        username=username,
        password_hash="x",
        role=role,
        tenant_id="default",
        is_active=active,
        email_encrypted=None,
        phone_encrypted=None,
    )


def test_pick_debug_user_prefers_admin_username():
    users = [
        _user("u2", "dev", UserRole.DEVELOPER),
        _user("u1", "admin", UserRole.ADMIN),
    ]
    picked = _pick_debug_user(users, "default")
    assert picked is not None
    assert picked.username == "admin"


def test_pick_debug_user_falls_back_to_active_admin():
    users = [
        _user("u2", "ops-user", UserRole.DEVELOPER),
        _user("u1", "root-user", UserRole.ADMIN),
    ]
    picked = _pick_debug_user(users, "default")
    assert picked is not None
    assert picked.username == "root-user"

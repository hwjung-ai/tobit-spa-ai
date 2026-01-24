"""Tests for permissions and access control."""

import importlib

import pytest
import sqlalchemy
from app.modules.auth.models import TbUser, UserRole
from app.modules.permissions.crud import (
    check_permission,
    get_role_permissions,
    grant_resource_permission,
    initialize_role_permissions,
    list_user_permissions,
    revoke_resource_permission,
)
from app.modules.permissions.models import (
    ResourcePermission,
    RolePermissionDefault,
    TbRolePermission,
)
from core.security import get_password_hash
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool


@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy import text

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Clear and reload models to avoid metadata caching
    try:
        for table_name in list(SQLModel.metadata.tables.keys()):
            del SQLModel.metadata.tables[table_name]
    except Exception:
        pass

    import app.modules.auth.models as auth_models  # noqa: F401
    import app.modules.permissions.models as perm_models  # noqa: F401

    importlib.reload(auth_models)
    importlib.reload(perm_models)

    # Drop all existing tables
    with engine.connect() as conn:
        inspector = sqlalchemy.inspect(engine)
        for table_name in inspector.get_table_names():
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            except Exception:
                pass
        try:
            conn.commit()
        except Exception:
            pass

    # Create all tables
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        if "already exists" in str(e):
            # Handle metadata caching issue
            with engine.begin() as conn:
                for table in SQLModel.metadata.tables.values():
                    try:
                        table.create(conn, checkfirst=True)
                    except Exception:
                        pass
        else:
            raise

    with Session(engine) as session:
        # Initialize default role permissions
        initialize_role_permissions(session)
        yield session


@pytest.fixture
def admin_user(session: Session) -> TbUser:
    """Create an admin user."""
    user = TbUser(
        id="admin-001",
        email_encrypted="admin@example.com",
        username="Admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        tenant_id="t1",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def manager_user(session: Session) -> TbUser:
    """Create a manager user."""
    user = TbUser(
        id="manager-001",
        email_encrypted="manager@example.com",
        username="Manager",
        password_hash=get_password_hash("manager123"),
        role=UserRole.MANAGER,
        tenant_id="t1",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def developer_user(session: Session) -> TbUser:
    """Create a developer user."""
    user = TbUser(
        id="dev-001",
        email_encrypted="dev@example.com",
        username="Developer",
        password_hash=get_password_hash("dev123"),
        role=UserRole.DEVELOPER,
        tenant_id="t1",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def viewer_user(session: Session) -> TbUser:
    """Create a viewer user."""
    user = TbUser(
        id="viewer-001",
        email_encrypted="viewer@example.com",
        username="Viewer",
        password_hash=get_password_hash("viewer123"),
        role=UserRole.VIEWER,
        tenant_id="t1",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class TestRolePermissions:
    """Test role-based permission defaults."""

    def test_admin_permissions(self):
        """Test admin has all permissions."""
        perms = get_role_permissions(UserRole.ADMIN)
        assert len(perms) > 0
        assert ResourcePermission.API_READ in perms
        assert ResourcePermission.API_DELETE in perms
        assert ResourcePermission.USER_DELETE in perms

    def test_manager_permissions(self):
        """Test manager has most permissions."""
        perms = get_role_permissions(UserRole.MANAGER)
        assert ResourcePermission.API_READ in perms
        assert ResourcePermission.API_DELETE in perms
        assert ResourcePermission.USER_DELETE not in perms

    def test_developer_permissions(self):
        """Test developer has read and execute."""
        perms = get_role_permissions(UserRole.DEVELOPER)
        assert ResourcePermission.API_READ in perms
        assert ResourcePermission.API_CREATE in perms
        assert ResourcePermission.API_EXECUTE in perms
        assert ResourcePermission.API_DELETE not in perms

    def test_viewer_permissions(self):
        """Test viewer has read-only."""
        perms = get_role_permissions(UserRole.VIEWER)
        assert ResourcePermission.API_READ in perms
        assert ResourcePermission.API_CREATE not in perms
        assert ResourcePermission.API_DELETE not in perms

    def test_initialize_role_permissions(self, session: Session):
        """Test initialization of default permissions."""
        stmt = select(TbRolePermission)
        perms = session.exec(stmt).all()
        assert len(perms) > 0

        # Check admin has permissions
        admin_perms = [p for p in perms if p.role == RolePermissionDefault.ADMIN]
        assert len(admin_perms) > 10


class TestPermissionChecks:
    """Test permission checking logic."""

    def test_admin_check_permission(self, session: Session, admin_user: TbUser):
        """Test admin can do anything."""
        result = check_permission(
            session,
            admin_user.id,
            admin_user.role,
            ResourcePermission.API_DELETE,
        )
        assert result.granted is True

    def test_developer_can_create_api(self, session: Session, developer_user: TbUser):
        """Test developer can create API."""
        result = check_permission(
            session,
            developer_user.id,
            developer_user.role,
            ResourcePermission.API_CREATE,
        )
        assert result.granted is True

    def test_developer_cannot_delete_api(
        self, session: Session, developer_user: TbUser
    ):
        """Test developer cannot delete API."""
        result = check_permission(
            session,
            developer_user.id,
            developer_user.role,
            ResourcePermission.API_DELETE,
        )
        assert result.granted is False

    def test_viewer_can_read(self, session: Session, viewer_user: TbUser):
        """Test viewer can only read."""
        result = check_permission(
            session,
            viewer_user.id,
            viewer_user.role,
            ResourcePermission.API_READ,
        )
        assert result.granted is True

    def test_viewer_cannot_write(self, session: Session, viewer_user: TbUser):
        """Test viewer cannot create."""
        result = check_permission(
            session,
            viewer_user.id,
            viewer_user.role,
            ResourcePermission.API_CREATE,
        )
        assert result.granted is False


class TestResourcePermissions:
    """Test resource-specific permission overrides."""

    def test_grant_resource_permission(
        self, session: Session, viewer_user: TbUser, admin_user: TbUser
    ):
        """Test granting specific resource permission."""
        perm = grant_resource_permission(
            session=session,
            user_id=viewer_user.id,
            resource_type="api",
            permission=ResourcePermission.API_UPDATE,
            resource_id="api-123",
            created_by_user_id=admin_user.id,
        )

        assert perm.user_id == viewer_user.id
        assert perm.resource_type == "api"
        assert perm.resource_id == "api-123"
        assert perm.permission == ResourcePermission.API_UPDATE

    def test_grant_resource_type_permission(
        self, session: Session, viewer_user: TbUser, admin_user: TbUser
    ):
        """Test granting permission for all resources of type."""
        perm = grant_resource_permission(
            session=session,
            user_id=viewer_user.id,
            resource_type="api",
            permission=ResourcePermission.API_CREATE,
            resource_id=None,  # All APIs
            created_by_user_id=admin_user.id,
        )

        assert perm.resource_id is None

    def test_check_resource_specific_permission(
        self, session: Session, viewer_user: TbUser, admin_user: TbUser
    ):
        """Test checking resource-specific permission."""
        # Grant permission to update specific API
        grant_resource_permission(
            session=session,
            user_id=viewer_user.id,
            resource_type="api",
            permission=ResourcePermission.API_UPDATE,
            resource_id="api-123",
            created_by_user_id=admin_user.id,
        )

        # Check permission for that specific resource
        result = check_permission(
            session,
            viewer_user.id,
            viewer_user.role,
            ResourcePermission.API_UPDATE,
            resource_type="api",
            resource_id="api-123",
        )

        assert result.granted is True
        assert "Resource-specific" in result.reason

    def test_check_resource_type_permission(
        self, session: Session, viewer_user: TbUser, admin_user: TbUser
    ):
        """Test checking resource-type permission."""
        # Grant permission to create all APIs
        grant_resource_permission(
            session=session,
            user_id=viewer_user.id,
            resource_type="api",
            permission=ResourcePermission.API_CREATE,
            resource_id=None,
            created_by_user_id=admin_user.id,
        )

        # Check for any API
        result = check_permission(
            session,
            viewer_user.id,
            viewer_user.role,
            ResourcePermission.API_CREATE,
            resource_type="api",
            resource_id="api-456",
        )

        assert result.granted is True

    def test_revoke_resource_permission(
        self, session: Session, viewer_user: TbUser, admin_user: TbUser
    ):
        """Test revoking resource permission."""
        grant_resource_permission(
            session=session,
            user_id=viewer_user.id,
            resource_type="api",
            permission=ResourcePermission.API_UPDATE,
            resource_id="api-123",
            created_by_user_id=admin_user.id,
        )

        # Revoke it
        success = revoke_resource_permission(
            session,
            viewer_user.id,
            "api",
            ResourcePermission.API_UPDATE,
            resource_id="api-123",
        )

        assert success is True

        # Verify it's gone
        result = check_permission(
            session,
            viewer_user.id,
            viewer_user.role,
            ResourcePermission.API_UPDATE,
            resource_type="api",
            resource_id="api-123",
        )

        assert result.granted is False


class TestPermissionExpiration:
    """Test permission expiration."""

    def test_expired_permission_denied(
        self, session: Session, viewer_user: TbUser, admin_user: TbUser
    ):
        """Test that expired permissions are denied."""
        from datetime import datetime, timedelta, timezone

        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)

        grant_resource_permission(
            session=session,
            user_id=viewer_user.id,
            resource_type="api",
            permission=ResourcePermission.API_UPDATE,
            resource_id="api-123",
            created_by_user_id=admin_user.id,
            expires_at=expired_time,
        )

        result = check_permission(
            session,
            viewer_user.id,
            viewer_user.role,
            ResourcePermission.API_UPDATE,
            resource_type="api",
            resource_id="api-123",
        )

        assert result.granted is False
        assert "expired" in result.reason.lower()

    def test_future_permission_allowed(
        self, session: Session, viewer_user: TbUser, admin_user: TbUser
    ):
        """Test that non-expired permissions work."""
        from datetime import datetime, timedelta, timezone

        future_time = datetime.now(timezone.utc) + timedelta(hours=1)

        grant_resource_permission(
            session=session,
            user_id=viewer_user.id,
            resource_type="api",
            permission=ResourcePermission.API_UPDATE,
            resource_id="api-123",
            created_by_user_id=admin_user.id,
            expires_at=future_time,
        )

        result = check_permission(
            session,
            viewer_user.id,
            viewer_user.role,
            ResourcePermission.API_UPDATE,
            resource_type="api",
            resource_id="api-123",
        )

        assert result.granted is True


class TestListPermissions:
    """Test listing user permissions."""

    def test_list_user_permissions(
        self, session: Session, developer_user: TbUser, admin_user: TbUser
    ):
        """Test listing all permissions for a user."""
        # Grant additional resource permission
        grant_resource_permission(
            session=session,
            user_id=developer_user.id,
            resource_type="api",
            permission=ResourcePermission.API_DELETE,
            resource_id="api-999",
            created_by_user_id=admin_user.id,
        )

        perms = list_user_permissions(session, developer_user.id, developer_user.role)

        assert len(perms["role_permissions"]) > 0
        assert len(perms["resource_permissions"]) > 0
        assert ResourcePermission.API_CREATE in perms["role_permissions"]

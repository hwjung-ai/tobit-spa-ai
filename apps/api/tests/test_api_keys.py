"""Tests for API Keys functionality."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from app.modules.api_keys.crud import (
    create_api_key,
    generate_api_key,
    get_api_key,
    get_api_key_scopes,
    has_scope,
    list_api_keys,
    revoke_api_key,
    validate_api_key,
)
from app.modules.auth.models import TbUser, UserRole
from core.db import get_session
from core.security import get_password_hash
from fastapi.testclient import TestClient
from main import app
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    from apps.api.app.modules.api_keys.models import TbApiKey
    from apps.api.app.modules.auth.models import TbRefreshToken, TbUser

    TbUser.metadata.create_all(engine)
    TbRefreshToken.metadata.create_all(engine)
    TbApiKey.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user(session: Session) -> TbUser:
    """Create a test user."""
    user = TbUser(
        id="test-user-001",
        email="test@example.com",
        username="Test User",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.DEVELOPER,
        tenant_id="t1",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def client(session: Session):
    """Create a test client."""
    def override_get_session():
        return session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


class TestApiKeyGeneration:
    """Test API key generation."""

    def test_generate_api_key(self):
        """Test generating a new API key."""
        key, key_hash = generate_api_key()

        assert key.startswith("sk_")
        assert len(key) > 20
        assert key_hash.startswith("$2b$")  # bcrypt hash

    def test_generate_unique_keys(self):
        """Test that generated keys are unique."""
        key1, hash1 = generate_api_key()
        key2, hash2 = generate_api_key()

        assert key1 != key2
        assert hash1 != hash2


class TestApiKeyCrud:
    """Test API Key CRUD operations."""

    def test_create_api_key(self, session: Session, test_user: TbUser):
        """Test creating an API key."""
        api_key, full_key = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Test Key",
            scope=["api:read", "api:write"],
        )

        assert api_key.user_id == test_user.id
        assert api_key.name == "Test Key"
        assert api_key.key_prefix == full_key[:8]
        assert api_key.is_active is True
        assert api_key.scope == json.dumps(["api:read", "api:write"])

    def test_create_api_key_with_expiration(self, session: Session, test_user: TbUser):
        """Test creating an API key with expiration."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        api_key, _ = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Expiring Key",
            scope=["api:read"],
            expires_at=expires_at,
        )

        assert api_key.expires_at is not None
        assert api_key.expires_at.date() == expires_at.date()

    def test_validate_api_key_valid(self, session: Session, test_user: TbUser):
        """Test validating a valid API key."""
        _, full_key = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Test Key",
            scope=["api:read"],
        )

        api_key = validate_api_key(session, full_key)

        assert api_key is not None
        assert api_key.user_id == test_user.id

    def test_validate_api_key_invalid(self, session: Session):
        """Test validating an invalid API key."""
        api_key = validate_api_key(session, "sk_invalid_key_that_does_not_exist")

        assert api_key is None

    def test_validate_api_key_expired(self, session: Session, test_user: TbUser):
        """Test validating an expired API key."""
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)

        api_key, full_key = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Expired Key",
            scope=["api:read"],
            expires_at=expired_time,
        )

        # Should return None for expired key
        result = validate_api_key(session, full_key)
        assert result is None

    def test_validate_api_key_inactive(self, session: Session, test_user: TbUser):
        """Test validating an inactive API key."""
        api_key, full_key = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Test Key",
            scope=["api:read"],
        )

        # Revoke the key
        revoke_api_key(session, api_key.id, test_user.id)

        # Should return None for inactive key
        result = validate_api_key(session, full_key)
        assert result is None

    def test_get_api_key(self, session: Session, test_user: TbUser):
        """Test retrieving a specific API key."""
        api_key, _ = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Test Key",
            scope=["api:read"],
        )

        retrieved = get_api_key(session, api_key.id, test_user.id)

        assert retrieved is not None
        assert retrieved.id == api_key.id
        assert retrieved.name == "Test Key"

    def test_get_api_key_wrong_user(self, session: Session, test_user: TbUser):
        """Test that users can't access other users' keys."""
        api_key, _ = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Test Key",
            scope=["api:read"],
        )

        retrieved = get_api_key(session, api_key.id, "different-user")

        assert retrieved is None

    def test_list_api_keys(self, session: Session, test_user: TbUser):
        """Test listing API keys."""
        create_api_key(session, test_user.id, "Key 1", ["api:read"])
        create_api_key(session, test_user.id, "Key 2", ["api:write"])
        create_api_key(session, test_user.id, "Key 3", ["api:read"])

        keys = list_api_keys(session, test_user.id)

        assert len(keys) == 3
        assert keys[0].name == "Key 3"  # Most recent first

    def test_list_api_keys_exclude_inactive(self, session: Session, test_user: TbUser):
        """Test listing API keys excludes inactive by default."""
        api_key1, _ = create_api_key(session, test_user.id, "Key 1", ["api:read"])
        api_key2, _ = create_api_key(session, test_user.id, "Key 2", ["api:write"])

        revoke_api_key(session, api_key2.id, test_user.id)

        keys = list_api_keys(session, test_user.id, include_inactive=False)

        assert len(keys) == 1
        assert keys[0].id == api_key1.id

    def test_list_api_keys_include_inactive(self, session: Session, test_user: TbUser):
        """Test listing API keys includes inactive when requested."""
        api_key1, _ = create_api_key(session, test_user.id, "Key 1", ["api:read"])
        api_key2, _ = create_api_key(session, test_user.id, "Key 2", ["api:write"])

        revoke_api_key(session, api_key2.id, test_user.id)

        keys = list_api_keys(session, test_user.id, include_inactive=True)

        assert len(keys) == 2

    def test_revoke_api_key(self, session: Session, test_user: TbUser):
        """Test revoking an API key."""
        api_key, _ = create_api_key(session, test_user.id, "Test Key", ["api:read"])

        success = revoke_api_key(session, api_key.id, test_user.id)

        assert success is True

        # Verify key is inactive
        updated = get_api_key(session, api_key.id, test_user.id)
        assert updated.is_active is False

    def test_revoke_nonexistent_key(self, session: Session, test_user: TbUser):
        """Test revoking a nonexistent key."""
        success = revoke_api_key(session, "nonexistent-id", test_user.id)

        assert success is False


class TestApiKeyScopes:
    """Test API key scope operations."""

    def test_get_api_key_scopes(self, session: Session, test_user: TbUser):
        """Test parsing API key scopes."""
        api_key, _ = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Test Key",
            scope=["api:read", "api:write"],
        )

        scopes = get_api_key_scopes(api_key)

        assert scopes == ["api:read", "api:write"]

    def test_has_scope_true(self, session: Session, test_user: TbUser):
        """Test checking scope when key has it."""
        api_key, _ = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Test Key",
            scope=["api:read", "api:write"],
        )

        assert has_scope(api_key, "api:read") is True
        assert has_scope(api_key, "api:write") is True

    def test_has_scope_false(self, session: Session, test_user: TbUser):
        """Test checking scope when key doesn't have it."""
        api_key, _ = create_api_key(
            session=session,
            user_id=test_user.id,
            name="Test Key",
            scope=["api:read"],
        )

        assert has_scope(api_key, "api:write") is False


class TestApiKeysRouter:
    """Test API Keys REST endpoints."""

    def test_create_api_key_endpoint(self, client: TestClient, test_user: TbUser):
        """Test creating an API key via REST endpoint."""
        # Note: In a real test, we'd need to mock authentication
        # This is a placeholder for integration testing
        pass

    def test_list_api_keys_endpoint(self, client: TestClient, test_user: TbUser):
        """Test listing API keys via REST endpoint."""
        pass

    def test_revoke_api_key_endpoint(self, client: TestClient, test_user: TbUser):
        """Test revoking an API key via REST endpoint."""
        pass

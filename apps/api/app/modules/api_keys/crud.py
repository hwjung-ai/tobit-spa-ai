"""CRUD operations for API Keys."""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from passlib.context import CryptContext
from sqlmodel import Session, select

from apps.api.app.modules.api_keys.models import TbApiKey, ApiKeyScope

# Password context for API key hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and return both the key and its hash.

    Returns:
        Tuple of (key, key_hash) where key is the full key to give to user
        and key_hash is the bcrypt hash to store in database
    """
    key = f"sk_{uuid4().hex}"
    key_hash = pwd_context.hash(key)
    return key, key_hash


def create_api_key(
    session: Session,
    user_id: str,
    name: str,
    scope: list[str],
    expires_at: Optional[datetime] = None,
    trace_id: str = "system",
) -> tuple[TbApiKey, str]:
    """
    Create a new API key for a user.

    Args:
        session: Database session
        user_id: User ID
        name: Human-readable name for the key
        scope: List of permission scopes
        expires_at: Optional expiration datetime
        trace_id: Trace ID for audit logging

    Returns:
        Tuple of (api_key_record, full_key) where full_key is only shown once
    """
    key, key_hash = generate_api_key()
    key_prefix = key[:8]

    api_key = TbApiKey(
        id=str(uuid4()),
        user_id=user_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scope=json.dumps(scope),
        is_active=True,
        expires_at=expires_at,
        created_by_trace_id=trace_id,
    )

    session.add(api_key)
    session.commit()
    session.refresh(api_key)

    return api_key, key


def validate_api_key(session: Session, key: str) -> Optional[TbApiKey]:
    """
    Validate an API key and return the associated API key record.

    Args:
        session: Database session
        key: The API key to validate

    Returns:
        TbApiKey record if valid, None otherwise
    """
    # Extract key prefix (first 8 chars)
    key_prefix = key[:8]

    # Query for active keys with matching prefix
    statement = select(TbApiKey).where(
        TbApiKey.key_prefix == key_prefix,
        TbApiKey.is_active == True,
    )

    candidates = session.exec(statement).all()

    # Verify full key against hash (only one should match)
    for candidate in candidates:
        # Check if expired
        if candidate.expires_at and candidate.expires_at <= datetime.now(timezone.utc):
            continue

        # Verify key hash
        if pwd_context.verify(key, candidate.key_hash):
            # Update last_used_at
            candidate.last_used_at = datetime.now(timezone.utc)
            session.add(candidate)
            session.commit()
            return candidate

    return None


def get_api_key(session: Session, key_id: str, user_id: str) -> Optional[TbApiKey]:
    """
    Get a specific API key.

    Args:
        session: Database session
        key_id: API key ID
        user_id: User ID (for authorization)

    Returns:
        TbApiKey record or None
    """
    statement = select(TbApiKey).where(
        TbApiKey.id == key_id,
        TbApiKey.user_id == user_id,
    )
    return session.exec(statement).first()


def list_api_keys(
    session: Session,
    user_id: str,
    include_inactive: bool = False,
) -> list[TbApiKey]:
    """
    List all API keys for a user.

    Args:
        session: Database session
        user_id: User ID
        include_inactive: Include inactive keys in results

    Returns:
        List of TbApiKey records
    """
    statement = select(TbApiKey).where(TbApiKey.user_id == user_id)

    if not include_inactive:
        statement = statement.where(TbApiKey.is_active == True)

    statement = statement.order_by(TbApiKey.created_at.desc())
    return session.exec(statement).all()


def revoke_api_key(
    session: Session,
    key_id: str,
    user_id: str,
) -> bool:
    """
    Revoke (deactivate) an API key.

    Args:
        session: Database session
        key_id: API key ID
        user_id: User ID (for authorization)

    Returns:
        True if revoked, False if not found
    """
    api_key = get_api_key(session, key_id, user_id)

    if not api_key:
        return False

    api_key.is_active = False
    api_key.updated_at = datetime.now(timezone.utc)
    session.add(api_key)
    session.commit()

    return True


def get_api_key_scopes(api_key: TbApiKey) -> list[str]:
    """
    Parse and return scopes from an API key.

    Args:
        api_key: TbApiKey record

    Returns:
        List of scope strings
    """
    try:
        return json.loads(api_key.scope)
    except (json.JSONDecodeError, TypeError):
        return []


def has_scope(api_key: TbApiKey, required_scope: str) -> bool:
    """
    Check if an API key has a specific scope.

    Args:
        api_key: TbApiKey record
        required_scope: Scope to check

    Returns:
        True if key has the scope
    """
    scopes = get_api_key_scopes(api_key)
    return required_scope in scopes or "*" in scopes

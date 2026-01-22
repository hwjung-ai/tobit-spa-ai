"""Authentication and authorization dependencies."""

from typing import Optional

from app.modules.api_keys.crud import validate_api_key
from app.modules.auth.models import TbUser, UserRole
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session

from core.config import get_settings
from core.db import get_session
from core.security import decode_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> TbUser:
    """
    Get the current authenticated user from JWT token.
    If enable_auth is False, returns a default debug user.

    Args:
        credentials: HTTP authorization credentials
        session: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    settings = get_settings()

    # If authentication is disabled, return a default debug user
    if not settings.enable_auth:
        debug_user = session.exec(
            session.query(TbUser).filter(TbUser.username == "admin@tobit.local")
        ).first()
        if debug_user:
            return debug_user
        # If no admin user exists, create a minimal user object for dev mode
        # This is a fallback for development without authentication setup
        return TbUser(
            id="dev-user",
            username="debug@dev",
            password_hash="",
            role=UserRole.ADMIN,
            tenant_id="dev-tenant",
            is_active=True,
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    settings = get_settings()

    try:
        payload = decode_token(
            token,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(TbUser, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def get_current_active_user(
    current_user: TbUser = Depends(get_current_user),
) -> TbUser:
    """
    Get current active user (additional validation).

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


def require_role(*required_roles: UserRole):
    """
    Factory for role-based access control.

    Args:
        required_roles: One or more required roles

    Returns:
        Dependency function that checks user role
    """
    def role_checker(current_user: TbUser = Depends(get_current_user)) -> TbUser:
        """Check if user has one of the required roles."""
        # Role hierarchy: VIEWER (0) < DEVELOPER (1) < MANAGER (2) < ADMIN (3)
        role_hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.DEVELOPER: 1,
            UserRole.MANAGER: 2,
            UserRole.ADMIN: 3,
        }

        user_level = role_hierarchy.get(current_user.role, -1)
        required_levels = [role_hierarchy.get(role, -1) for role in required_roles]

        if user_level < max(required_levels):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in required_roles]}",
            )
        return current_user

    return role_checker


def get_current_user_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> tuple[TbUser, Optional[str]]:
    """
    Get current user from either JWT token or API key.

    Returns a tuple of (user, api_key_scope_str) where api_key_scope_str is
    only set if authenticated via API key, None otherwise.

    Args:
        credentials: HTTP authorization credentials
        session: Database session

    Returns:
        Tuple of (current_user, api_key_scopes) where scopes are comma-separated

    Raises:
        HTTPException: If neither JWT token nor API key is valid
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Try JWT token first
    settings = get_settings()
    try:
        payload = decode_token(
            token,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
        )

        if payload.get("type") == "access":
            user_id: str = payload.get("sub")
            if user_id:
                user = session.get(TbUser, user_id)
                if user and user.is_active:
                    return user, None
    except JWTError:
        pass

    # Try API key as fallback
    api_key = validate_api_key(session, token)
    if api_key:
        user = session.get(TbUser, api_key.user_id)
        if user and user.is_active:
            scopes = api_key.scope  # JSON string
            return user, scopes

    # Neither worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

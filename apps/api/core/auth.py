"""Authentication and authorization dependencies."""

import json
from typing import Optional

from app.modules.api_keys.crud import get_api_key_scopes, validate_api_key
from app.modules.auth.models import TbUser, UserRole
from app.modules.operation_settings.crud import get_setting_effective_value
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from models.api_definition import ApiAuthMode, ApiDefinition
from sqlmodel import Session, select

from core.config import get_settings
from core.db import get_session
from core.security import decode_token

security = HTTPBearer(auto_error=False)


def _unwrap_api_definition(result) -> ApiDefinition | None:
    if isinstance(result, ApiDefinition):
        return result
    mapping = getattr(result, "_mapping", None)
    if mapping is not None:
        direct = mapping.get(ApiDefinition)
        if isinstance(direct, ApiDefinition):
            return direct
        for value in mapping.values():
            if isinstance(value, ApiDefinition):
                return value
    if isinstance(result, (tuple, list)) and result:
        first = result[0]
        if isinstance(first, ApiDefinition):
            return first
    return None


def _resolve_runtime_api_policy(
    session: Session, request: Request, settings
) -> tuple[str, list[str], bool]:
    """Resolve auth policy for /runtime/* request."""
    default_mode_effective = get_setting_effective_value(
        session=session,
        setting_key="api_auth_default_mode",
        default_value=settings.api_auth_default_mode,
        env_value=settings.api_auth_default_mode,
    )
    enforce_scopes_effective = get_setting_effective_value(
        session=session,
        setting_key="api_auth_enforce_scopes",
        default_value=settings.api_auth_enforce_scopes,
        env_value=settings.api_auth_enforce_scopes,
    )
    default_mode = str(default_mode_effective.get("value") or "jwt_only")
    enforce_scopes = bool(enforce_scopes_effective.get("value", True))

    full_path = request.url.path
    runtime_idx = full_path.find("/runtime/")
    if runtime_idx >= 0:
        full_path = full_path[runtime_idx:]
    method = request.method.upper()
    normalized = f"/{full_path.lstrip('/')}"
    if normalized.startswith("/runtime/"):
        normalized = normalized[len("/runtime") :]
        normalized = f"/{normalized.lstrip('/')}"
    candidates = [normalized, f"/runtime{normalized}", f"/{normalized.lstrip('/')}"]
    api = _unwrap_api_definition(
        session.exec(
        select(ApiDefinition)
        .where(ApiDefinition.path.in_(candidates))
        .where(ApiDefinition.method == method)
        .where(ApiDefinition.is_enabled)
        .limit(1)
    ).first()
    )
    if not api:
        return default_mode, [], enforce_scopes

    mode = str(getattr(api, "auth_mode", None) or default_mode)
    scopes = getattr(api, "required_scopes", None) or []
    if isinstance(scopes, str):
        try:
            scopes = json.loads(scopes)
        except json.JSONDecodeError:
            scopes = []
    if not isinstance(scopes, list):
        scopes = []
    return mode, [str(scope) for scope in scopes], enforce_scopes


def _authenticate_jwt_only(token: str, session: Session, settings) -> TbUser:
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


def _authenticate_api_key_only(
    token: str,
    session: Session,
    required_scopes: list[str] | None = None,
    enforce_scopes: bool = True,
) -> TbUser:
    api_key = validate_api_key(session, token)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.get(TbUser, api_key.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scopes = get_api_key_scopes(api_key)
    if enforce_scopes and required_scopes:
        if "*" not in scopes and any(scope not in scopes for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key does not have required scopes",
            )

    setattr(user, "_auth_mode", "api_key")
    setattr(user, "_api_key_scopes", scopes)
    return user


def get_current_user(
    request: Request,
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
            select(TbUser).where(TbUser.username == "admin@tobit.local")
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

    # Runtime APIs can use policy-driven hybrid authentication.
    if request is not None and "/runtime/" in request.url.path:
        mode, required_scopes, enforce_scopes = _resolve_runtime_api_policy(
            session=session,
            request=request,
            settings=settings,
        )
        if mode == ApiAuthMode.api_key_only.value:
            return _authenticate_api_key_only(
                token=token,
                session=session,
                required_scopes=required_scopes,
                enforce_scopes=enforce_scopes,
            )
        if mode == ApiAuthMode.jwt_or_api_key.value:
            try:
                return _authenticate_jwt_only(token, session, settings)
            except HTTPException:
                return _authenticate_api_key_only(
                    token=token,
                    session=session,
                    required_scopes=required_scopes,
                    enforce_scopes=enforce_scopes,
                )
        # Default and fallback to strict JWT-only.
        return _authenticate_jwt_only(token, session, settings)

    return _authenticate_jwt_only(token, session, settings)


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
        settings = get_settings()
        if not settings.enable_permission_check:
            return current_user

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

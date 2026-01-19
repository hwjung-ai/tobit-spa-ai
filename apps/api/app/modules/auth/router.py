"""Authentication router for login, logout, and token refresh."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from apps.api.app.modules.auth.models import (
    TbRefreshToken,
    TbUser,
    TbUserRead,
    UserRole,
)
from apps.api.core.auth import get_current_user
from apps.api.core.config import get_settings
from apps.api.core.db import get_session
from apps.api.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from apps.api.schemas.common import ResponseEnvelope

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request schema."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: TbUserRead


class RefreshRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class AccessTokenResponse(BaseModel):
    """Access token only response."""
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=ResponseEnvelope)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    User login endpoint.

    Args:
        payload: Login credentials (email, password)
        session: Database session

    Returns:
        ResponseEnvelope with access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid or user is inactive
    """
    # Find user by email (using username field as email is encrypted and not searchable)
    statement = select(TbUser).where(TbUser.username == payload.email)
    user = session.exec(statement).first()

    # Verify user exists and password matches
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    settings = get_settings()

    # Create tokens
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email, # This uses the property we added
            "role": user.role,
            "tenant_id": user.tenant_id,
        },
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    refresh_token = create_refresh_token(
        data={"sub": user.id},
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )

    # Store refresh token in database
    refresh_token_record = TbRefreshToken(
        id=str(uuid4()),
        user_id=user.id,
        token_hash=refresh_token,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    session.add(refresh_token_record)

    # Update last login time
    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()

    return ResponseEnvelope.success(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": TbUserRead.model_validate(user),
        }
    )


@router.post("/refresh", response_model=ResponseEnvelope)
def refresh(
    payload: RefreshRequest,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Refresh access token using refresh token.

    Args:
        payload: Refresh token
        session: Database session

    Returns:
        ResponseEnvelope with new access token

    Raises:
        HTTPException: If refresh token is invalid
    """
    settings = get_settings()

    # Decode and validate refresh token
    try:
        token_payload = decode_token(
            payload.refresh_token,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )

    # Verify token type
    if token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Get user
    user_id = token_payload.get("sub")
    user = session.get(TbUser, user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token or user inactive",
        )

    # Create new access token
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id,
        },
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return ResponseEnvelope.success(
        data={
            "access_token": access_token,
            "token_type": "bearer",
        }
    )


@router.post("/logout", response_model=ResponseEnvelope)
def logout(
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Logout by invalidating all active refresh tokens.

    Args:
        current_user: Current authenticated user
        session: Database session

    Returns:
        ResponseEnvelope with success message
    """
    # Invalidate all active refresh tokens for this user
    statement = select(TbRefreshToken).where(
        TbRefreshToken.user_id == current_user.id,
        TbRefreshToken.revoked_at.is_(None),
    )
    tokens = session.exec(statement).all()

    for token in tokens:
        token.revoked_at = datetime.now(timezone.utc)
        session.add(token)

    session.commit()

    return ResponseEnvelope.success(data={"message": "Logged out successfully"})


@router.get("/me", response_model=ResponseEnvelope)
def get_current_user_info(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        ResponseEnvelope with user information
    """
    return ResponseEnvelope.success(
        data={
            "user": TbUserRead.model_validate(current_user),
        }
    )

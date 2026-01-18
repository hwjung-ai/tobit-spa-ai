"""Authentication models for user management and token storage."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class TbUserBase(SQLModel):
    """Base user model."""
    email: str = Field(max_length=255)
    username: str = Field(max_length=100)
    password_hash: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.VIEWER)
    tenant_id: str = Field(max_length=64, index=True)
    is_active: bool = Field(default=True)
    last_login_at: Optional[datetime] = None


class TbUser(TbUserBase, table=True):
    """User account table."""
    __tablename__ = "tb_user"

    id: str = Field(
        primary_key=True,
        max_length=36,
        default_factory=lambda: str(uuid4())
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class TbUserRead(TbUserBase):
    """User read schema (without password hash)."""
    id: str


class TbRefreshTokenBase(SQLModel):
    """Base refresh token model."""
    user_id: str = Field(foreign_key="tb_user.id", index=True, max_length=36)
    token_hash: str = Field(max_length=255)
    expires_at: datetime
    revoked_at: Optional[datetime] = None


class TbRefreshToken(TbRefreshTokenBase, table=True):
    """Refresh token storage table."""
    __tablename__ = "tb_refresh_token"

    id: str = Field(
        primary_key=True,
        max_length=36,
        default_factory=lambda: str(uuid4())
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

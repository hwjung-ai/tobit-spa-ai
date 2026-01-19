"""Authentication models for user management and token storage."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel

from core.encryption import get_encryption_manager


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class TbUserBase(SQLModel):
    """Base user model."""
    username: str = Field(max_length=100)
    password_hash: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.VIEWER)
    tenant_id: str = Field(max_length=64, index=True)
    is_active: bool = Field(default=True)
    last_login_at: Optional[datetime] = None
    # Encrypted fields (stored encrypted in database)
    email_encrypted: str = Field(max_length=512, description="Encrypted email address")
    phone_encrypted: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Encrypted phone number"
    )


class TbUser(TbUserBase, table=True):
    """User account table."""
    __tablename__ = "tb_user"
    __table_args__ = ({"extend_existing": True},)

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

    def get_email(self) -> str:
        """Decrypt and return email address."""
        if not self.email_encrypted:
            return ""
        try:
            manager = get_encryption_manager()
            return manager.decrypt(self.email_encrypted)
        except ValueError:
            # Return as-is if decryption fails (backward compatibility)
            return self.email_encrypted

    def set_email(self, email: str) -> None:
        """Encrypt and store email address."""
        if not email:
            self.email_encrypted = ""
            return
        try:
            manager = get_encryption_manager()
            self.email_encrypted = manager.encrypt(email)
        except ValueError:
            # Store plaintext if encryption fails
            self.email_encrypted = email

    def get_phone(self) -> Optional[str]:
        """Decrypt and return phone number."""
        if not self.phone_encrypted:
            return None
        try:
            manager = get_encryption_manager()
            return manager.decrypt(self.phone_encrypted)
        except ValueError:
            # Return as-is if decryption fails
            return self.phone_encrypted

    def set_phone(self, phone: Optional[str]) -> None:
        """Encrypt and store phone number."""
        if not phone:
            self.phone_encrypted = None
            return
        try:
            manager = get_encryption_manager()
            self.phone_encrypted = manager.encrypt(phone)
        except ValueError:
            # Store plaintext if encryption fails
            self.phone_encrypted = phone

    @property
    def email(self) -> str:
        """Property to get decrypted email."""
        return self.get_email()


class TbUserRead(TbUserBase):
    """User read schema (without password hash)."""
    id: str
    email: str | None = None


class TbRefreshTokenBase(SQLModel):
    """Base refresh token model."""
    user_id: str = Field(foreign_key="tb_user.id", index=True, max_length=36)
    token_hash: str = Field(max_length=255)
    expires_at: datetime
    revoked_at: Optional[datetime] = None


class TbRefreshToken(TbRefreshTokenBase, table=True):
    """Refresh token storage table."""
    __tablename__ = "tb_refresh_token"
    __table_args__ = ({"extend_existing": True},)

    id: str = Field(
        primary_key=True,
        max_length=36,
        default_factory=lambda: str(uuid4())
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

"""Data encryption utilities for sensitive fields."""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption manager.

        Args:
            encryption_key: Base64-encoded Fernet key. If None, reads from
                          ENCRYPTION_KEY environment variable.

        Raises:
            ValueError: If no encryption key is available or invalid
        """
        key = encryption_key or os.getenv("ENCRYPTION_KEY")

        if not key:
            raise ValueError(
                "No encryption key provided. Set ENCRYPTION_KEY environment variable "
                "or pass encryption_key parameter."
            )

        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {str(e)}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            ValueError: If plaintext is None or encryption fails
        """
        if plaintext is None:
            raise ValueError("Cannot encrypt None value")

        try:
            ciphertext = self.cipher.encrypt(plaintext.encode("utf-8"))
            return ciphertext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Encrypted string to decrypt

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If ciphertext is None or decryption fails
        """
        if ciphertext is None:
            raise ValueError("Cannot decrypt None value")

        try:
            plaintext = self.cipher.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.

        Returns:
            Base64-encoded Fernet key (safe to store in config)

        Usage:
            key = EncryptionManager.generate_key()
            export ENCRYPTION_KEY="{key}"
        """
        return Fernet.generate_key().decode("utf-8")

    @staticmethod
    def derive_key_from_password(password: str, salt: str = "tobit-spa-ai") -> str:
        """
        Derive encryption key from password (for backup/alternative key generation).

        Args:
            password: Master password
            salt: Salt for key derivation (default uses app name)

        Returns:
            Base64-encoded Fernet key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # Fernet key size
            salt=salt.encode("utf-8"),
            iterations=100000,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        return key.decode("utf-8")


class EncryptedString:
    """Descriptor for automatically encrypted/decrypted string fields."""

    def __init__(self, encryption_manager: Optional[EncryptionManager] = None):
        """
        Initialize encrypted string descriptor.

        Args:
            encryption_manager: EncryptionManager instance to use
        """
        self.encryption_manager = encryption_manager
        self.name: Optional[str] = None

    def __set_name__(self, owner, name: str):
        """Store the attribute name."""
        self.name = f"_{name}"

    def __get__(self, obj, objtype=None):
        """Get and decrypt the value."""
        if obj is None:
            return self

        value = getattr(obj, self.name, None)
        if value is None:
            return None

        manager = self.encryption_manager or EncryptionManager()
        try:
            return manager.decrypt(value)
        except ValueError:
            # Return as-is if not encrypted (for backward compatibility)
            return value

    def __set__(self, obj, value: Optional[str]):
        """Encrypt and set the value."""
        if value is None:
            setattr(obj, self.name, None)
            return

        manager = self.encryption_manager or EncryptionManager()
        encrypted = manager.encrypt(value)
        setattr(obj, self.name, encrypted)


def get_encryption_manager() -> EncryptionManager:
    """
    Get the application's encryption manager instance.

    Returns:
        EncryptionManager configured with app's encryption key

    Raises:
        ValueError: If encryption key is not configured
    """
    return EncryptionManager()

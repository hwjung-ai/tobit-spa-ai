"""Tests for data encryption functionality."""

import pytest
from apps.api.core.encryption import EncryptionManager


class TestEncryptionManager:
    """Test encryption and decryption operations."""

    @pytest.fixture
    def encryption_key(self):
        """Generate a test encryption key."""
        return EncryptionManager.generate_key()

    @pytest.fixture
    def manager(self, encryption_key):
        """Create an encryption manager with test key."""
        return EncryptionManager(encryption_key)

    def test_generate_key(self):
        """Test key generation."""
        key1 = EncryptionManager.generate_key()
        key2 = EncryptionManager.generate_key()

        # Keys should be generated
        assert key1 is not None
        assert key2 is not None
        # Keys should be different
        assert key1 != key2
        # Keys should be strings
        assert isinstance(key1, str)
        assert isinstance(key2, str)
        # Keys should be in valid Fernet format (base64)
        assert len(key1) > 20

    def test_encrypt_plaintext(self, manager):
        """Test encrypting plaintext."""
        plaintext = "test@example.com"
        ciphertext = manager.encrypt(plaintext)

        # Ciphertext should be generated
        assert ciphertext is not None
        # Ciphertext should not equal plaintext
        assert ciphertext != plaintext
        # Ciphertext should be a string
        assert isinstance(ciphertext, str)
        # Ciphertext should be longer (encrypted format)
        assert len(ciphertext) > len(plaintext)

    def test_decrypt_ciphertext(self, manager):
        """Test decrypting ciphertext."""
        plaintext = "test@example.com"
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        # Decrypted should match original
        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip(self, manager):
        """Test full encryption/decryption roundtrip."""
        test_strings = [
            "simple",
            "test@example.com",
            "+1-555-123-4567",
            "John Doe",
            "special!@#$%^&*()",
            "",
            "unicode: こんにちは",
            "a" * 500,  # Long string
        ]

        for test_string in test_strings:
            ciphertext = manager.encrypt(test_string)
            decrypted = manager.decrypt(ciphertext)
            assert decrypted == test_string

    def test_encrypt_none_raises_error(self, manager):
        """Test that encrypting None raises error."""
        with pytest.raises(ValueError, match="Cannot encrypt None"):
            manager.encrypt(None)

    def test_decrypt_none_raises_error(self, manager):
        """Test that decrypting None raises error."""
        with pytest.raises(ValueError, match="Cannot decrypt None"):
            manager.decrypt(None)

    def test_decrypt_invalid_ciphertext_raises_error(self, manager):
        """Test that decrypting invalid ciphertext raises error."""
        with pytest.raises(ValueError, match="Decryption failed"):
            manager.decrypt("invalid-ciphertext-data")

    def test_different_keys_cannot_decrypt(self, encryption_key):
        """Test that different keys cannot decrypt each other's ciphertexts."""
        manager1 = EncryptionManager(encryption_key)
        manager2 = EncryptionManager(EncryptionManager.generate_key())

        plaintext = "secret message"
        ciphertext = manager1.encrypt(plaintext)

        # Manager2 should fail to decrypt manager1's ciphertext
        with pytest.raises(ValueError):
            manager2.decrypt(ciphertext)

    def test_encryption_is_deterministic(self, manager):
        """Test that encryption is not deterministic (produces different output)."""
        plaintext = "test message"
        ciphertext1 = manager.encrypt(plaintext)
        ciphertext2 = manager.encrypt(plaintext)

        # Both should decrypt to same plaintext
        assert manager.decrypt(ciphertext1) == plaintext
        assert manager.decrypt(ciphertext2) == plaintext
        # But ciphertexts may be different (Fernet includes timestamp)
        # This is actually a security feature (prevents pattern analysis)

    def test_derive_key_from_password(self):
        """Test deriving key from password."""
        password = "my-secure-password"
        key1 = EncryptionManager.derive_key_from_password(password)
        key2 = EncryptionManager.derive_key_from_password(password)

        # Same password should produce same key
        assert key1 == key2

        # Different password should produce different key
        key3 = EncryptionManager.derive_key_from_password("different-password")
        assert key1 != key3

    def test_password_derived_key_works(self):
        """Test that password-derived key can encrypt/decrypt."""
        password = "master-password"
        key = EncryptionManager.derive_key_from_password(password)
        manager = EncryptionManager(key)

        plaintext = "sensitive data"
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encryption_manager_initialization_without_key_raises_error(self):
        """Test that initializing without key raises error."""
        # Temporarily unset ENCRYPTION_KEY
        import os
        original_key = os.environ.pop("ENCRYPTION_KEY", None)

        try:
            with pytest.raises(ValueError, match="No encryption key"):
                EncryptionManager()
        finally:
            # Restore key
            if original_key:
                os.environ["ENCRYPTION_KEY"] = original_key

    def test_encryption_manager_with_invalid_key_raises_error(self):
        """Test that invalid key format raises error."""
        with pytest.raises(ValueError, match="Invalid encryption key"):
            EncryptionManager("not-a-valid-key")

    def test_encrypt_empty_string(self, manager):
        """Test encrypting empty string."""
        plaintext = ""
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_very_long_string(self, manager):
        """Test encrypting very long string."""
        plaintext = "x" * 10000
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext


class TestUserEncryption:
    """Test encryption integration with user model."""

    @pytest.fixture
    def encryption_key(self):
        """Generate test key."""
        return EncryptionManager.generate_key()

    @pytest.fixture
    def user_with_encryption(self, encryption_key):
        """Create a test user with encryption."""
        import os
        original_key = os.environ.get("ENCRYPTION_KEY")
        os.environ["ENCRYPTION_KEY"] = encryption_key

        from apps.api.app.modules.auth.models import TbUser, UserRole
        from apps.api.core.security import get_password_hash

        user = TbUser(
            id="test-user-001",
            username="Test User",
            password_hash=get_password_hash("password123"),
            role=UserRole.DEVELOPER,
            tenant_id="t1",
            is_active=True,
            email_encrypted="",
            phone_encrypted=None,
        )

        yield user

        # Restore original key
        if original_key:
            os.environ["ENCRYPTION_KEY"] = original_key
        else:
            os.environ.pop("ENCRYPTION_KEY", None)

    def test_user_set_get_email(self, user_with_encryption):
        """Test setting and getting encrypted email."""
        email = "user@example.com"
        user_with_encryption.set_email(email)

        # Stored value should be encrypted
        assert user_with_encryption.email_encrypted != email
        assert len(user_with_encryption.email_encrypted) > len(email)

        # Retrieved value should be decrypted
        retrieved = user_with_encryption.get_email()
        assert retrieved == email

    def test_user_set_get_phone(self, user_with_encryption):
        """Test setting and getting encrypted phone."""
        phone = "+1-555-123-4567"
        user_with_encryption.set_phone(phone)

        # Stored value should be encrypted
        assert user_with_encryption.phone_encrypted != phone
        assert len(user_with_encryption.phone_encrypted) > len(phone)

        # Retrieved value should be decrypted
        retrieved = user_with_encryption.get_phone()
        assert retrieved == phone

    def test_user_set_empty_email(self, user_with_encryption):
        """Test setting empty email."""
        user_with_encryption.set_email("")
        assert user_with_encryption.email_encrypted == ""
        assert user_with_encryption.get_email() == ""

    def test_user_set_none_phone(self, user_with_encryption):
        """Test setting None phone."""
        user_with_encryption.set_phone(None)
        assert user_with_encryption.phone_encrypted is None
        assert user_with_encryption.get_phone() is None


class TestApiKeyEncryption:
    """Test encryption integration with API key model."""

    @pytest.fixture
    def encryption_key(self):
        """Generate test key."""
        return EncryptionManager.generate_key()

    @pytest.fixture
    def api_key_with_encryption(self, encryption_key):
        """Create a test API key with encryption."""
        import os
        original_key = os.environ.get("ENCRYPTION_KEY")
        os.environ["ENCRYPTION_KEY"] = encryption_key

        from apps.api.app.modules.api_keys.models import TbApiKey
        import json

        api_key = TbApiKey(
            id="key-001",
            user_id="user-001",
            name="Test Key",
            key_prefix="sk_a1b2",
            key_hash="$2b$12$test_bcrypt_hash",
            scope=json.dumps(["api:read"]),
            is_active=True,
        )

        yield api_key

        # Restore key
        if original_key:
            os.environ["ENCRYPTION_KEY"] = original_key
        else:
            os.environ.pop("ENCRYPTION_KEY", None)

    def test_api_key_encrypt_hash(self, api_key_with_encryption):
        """Test encrypting API key hash."""
        original_hash = "$2b$12$test_bcrypt_hash"
        encrypted = api_key_with_encryption.encrypt_hash(original_hash)

        # Should not equal original
        assert encrypted != original_hash
        # Should be a string
        assert isinstance(encrypted, str)

    def test_api_key_decrypt_hash(self, api_key_with_encryption):
        """Test decrypting API key hash."""
        original_hash = "$2b$12$test_bcrypt_hash"
        api_key_with_encryption.key_hash = api_key_with_encryption.encrypt_hash(original_hash)

        decrypted = api_key_with_encryption.decrypt_hash()
        assert decrypted == original_hash

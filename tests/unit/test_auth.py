"""Unit tests for authentication and JWT handling."""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt

from usms.api.config import get_settings
from usms.api.dependencies import (
    _decrypt_password,
    _encrypt_password,
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from usms.api.models.auth import TokenData


class TestPasswordEncryption:
    """Tests for password encryption/decryption."""

    def test_encrypt_decrypt_password(self):
        """Test that password encryption/decryption works correctly."""
        original_password = "my_secret_password_123"
        encrypted = _encrypt_password(original_password)
        decrypted = _decrypt_password(encrypted)

        assert decrypted == original_password
        assert encrypted != original_password  # Encrypted should be different

    def test_encrypt_different_passwords_different_output(self):
        """Test that different passwords produce different encrypted outputs."""
        password1 = "password1"
        password2 = "password2"

        encrypted1 = _encrypt_password(password1)
        encrypted2 = _encrypt_password(password2)

        assert encrypted1 != encrypted2

    def test_decrypt_invalid_password_raises_error(self):
        """Test that decrypting invalid data raises an error."""
        with pytest.raises(Exception):  # Fernet will raise InvalidToken
            _decrypt_password("invalid_encrypted_data")


class TestPasswordHashing:
    """Tests for bcrypt password hashing (for future user auth)."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_pass"  # Short password for bcrypt
        hashed = get_password_hash(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash format

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "correct_pass"  # Short password for bcrypt
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "correct_pass"  # Short password for bcrypt
        wrong_password = "wrong_pass"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False


class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token(self, test_username, test_password):
        """Test creating a valid access token."""
        token, expires_in = create_access_token(test_username, test_password)

        assert isinstance(token, str)
        assert isinstance(expires_in, int)
        assert expires_in > 0

        # Verify token can be decoded
        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        assert payload["username"] == test_username
        assert "password" in payload
        assert "sub" in payload  # user_id
        assert "exp" in payload  # expiration

    def test_create_access_token_password_encrypted(self, test_username, test_password):
        """Test that password in token is encrypted, not plain."""
        token, _ = create_access_token(test_username, test_password)

        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        # Password should be encrypted (different from original)
        assert payload["password"] != test_password

        # But should be decryptable
        decrypted = _decrypt_password(payload["password"])
        assert decrypted == test_password

    def test_create_access_token_expiration(self, test_username, test_password):
        """Test that token has correct expiration time."""
        token, expires_in = create_access_token(test_username, test_password)

        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        exp_datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        # Expiration should be in the future
        assert exp_datetime > now

        # Should match configured expiration time (with some tolerance)
        expected_exp = now + timedelta(seconds=settings.JWT_EXPIRATION)
        time_diff = abs((exp_datetime - expected_exp).total_seconds())
        assert time_diff < 5  # Within 5 seconds


class TestTokenVerification:
    """Tests for JWT token verification."""

    def test_verify_valid_token(self, valid_token, test_username):
        """Test verifying a valid token."""
        token, _ = valid_token
        token_data = verify_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.username == test_username
        assert token_data.user_id is not None
        assert token_data.password is not None  # Encrypted password
        assert isinstance(token_data.exp, datetime)

    def test_verify_expired_token(self, expired_token):
        """Test that expired tokens are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token(expired_token)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    def test_verify_invalid_signature(self, test_username, test_password):
        """Test that tokens with invalid signature are rejected."""
        settings = get_settings()

        # Create token with wrong secret
        payload = {
            "sub": "test_user",
            "username": test_username,
            "password": "encrypted",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        invalid_token = jwt.encode(payload, "wrong_secret", algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)

        assert exc_info.value.status_code == 401

    def test_verify_token_missing_fields(self):
        """Test that tokens with missing required fields are rejected."""
        settings = get_settings()

        # Create token without username
        payload = {
            "sub": "test_user",
            "password": "encrypted",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        invalid_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "missing required fields" in exc_info.value.detail

    def test_verify_malformed_token(self):
        """Test that malformed tokens are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("not.a.valid.jwt.token")

        assert exc_info.value.status_code == 401


class TestTokenDataExtraction:
    """Tests for extracting and decrypting data from tokens."""

    def test_extract_and_decrypt_password(self, valid_token, test_password):
        """Test that password can be extracted and decrypted from token."""
        token, _ = valid_token
        token_data = verify_token(token)

        # Password should be encrypted in token
        assert token_data.password != test_password

        # But should decrypt to original
        decrypted = _decrypt_password(token_data.password)
        assert decrypted == test_password

    def test_user_id_consistent(self, test_username):
        """Test that same username always produces same user_id."""
        token1, _ = create_access_token(test_username, "password1")
        token2, _ = create_access_token(test_username, "password2")

        data1 = verify_token(token1)
        data2 = verify_token(token2)

        assert data1.user_id == data2.user_id

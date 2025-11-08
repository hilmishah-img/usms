"""FastAPI dependencies for authentication and account injection."""

import hashlib
import httpx
from datetime import datetime, timedelta, timezone
from typing import Annotated

from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from usms import initialize_usms_account
from usms.api.config import get_settings
from usms.api.models.auth import TokenData
from usms.exceptions.errors import USMSLoginError, USMSMissingCredentialsError
from usms.services.account import BaseUSMSAccount

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_encryption_key() -> bytes:
    """Get or generate encryption key from JWT secret.

    Returns
    -------
    bytes
        32-byte Fernet encryption key derived from JWT secret
    """
    settings = get_settings()
    # Derive a 32-byte key from JWT_SECRET for Fernet encryption
    # Use SHA256 to ensure we always get exactly 32 bytes
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    return Fernet(Fernet.generate_key() if len(key) != 32 else key)


def _encrypt_password(password: str) -> str:
    """Encrypt password using Fernet (reversible encryption).

    Parameters
    ----------
    password : str
        Plain text password

    Returns
    -------
    str
        Base64-encoded encrypted password
    """
    settings = get_settings()
    # Create Fernet cipher using JWT secret as base
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    key_base64 = Fernet.generate_key()[:32]  # Get proper Fernet key format
    # Use first 32 bytes of SHA256 hash as Fernet key
    import base64
    fernet_key = base64.urlsafe_b64encode(key)
    cipher = Fernet(fernet_key)
    encrypted = cipher.encrypt(password.encode())
    return encrypted.decode()


def _decrypt_password(encrypted_password: str) -> str:
    """Decrypt password using Fernet.

    Parameters
    ----------
    encrypted_password : str
        Base64-encoded encrypted password

    Returns
    -------
    str
        Decrypted plain text password
    """
    settings = get_settings()
    # Create Fernet cipher using same JWT secret
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    import base64
    fernet_key = base64.urlsafe_b64encode(key)
    cipher = Fernet(fernet_key)
    decrypted = cipher.decrypt(encrypted_password.encode())
    return decrypted.decode()


def create_access_token(username: str, password: str) -> tuple[str, int]:
    """Create JWT access token with encrypted credentials.

    Parameters
    ----------
    username : str
        USMS username (IC number)
    password : str
        USMS password (will be encrypted with Fernet)

    Returns
    -------
    tuple[str, int]
        Tuple of (access_token, expires_in_seconds)

    Notes
    -----
    The token contains:
    - username (plain)
    - password (encrypted with Fernet - reversible)
    - user_id (hash of username for identification)
    - exp (expiration timestamp)
    """
    settings = get_settings()

    # Create user ID hash for identification
    user_id = hashlib.sha256(username.encode()).hexdigest()[:16]

    # Encrypt password (reversible encryption)
    encrypted_password = _encrypt_password(password)

    # Calculate expiration
    expires_delta = timedelta(seconds=settings.JWT_EXPIRATION)
    expire = datetime.now(timezone.utc) + expires_delta

    # Create token payload
    token_data = {
        "sub": user_id,  # Subject (user identifier)
        "username": username,
        "password": encrypted_password,
        "exp": expire,
    }

    # Encode JWT
    access_token = jwt.encode(
        token_data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

    return access_token, settings.JWT_EXPIRATION


def verify_token(token: str) -> TokenData:
    """Verify JWT token and extract data.

    Parameters
    ----------
    token : str
        JWT access token

    Returns
    -------
    TokenData
        Extracted token data

    Raises
    ------
    HTTPException
        If token is invalid or expired (401)
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )

        username: str = payload.get("username")
        password: str = payload.get("password")
        user_id: str = payload.get("sub")
        exp_timestamp: int = payload.get("exp")

        if not username or not password or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing required fields",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Convert expiration timestamp to datetime
        exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        return TokenData(
            username=username, password=password, user_id=user_id, exp=exp
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenData:
    """Extract and verify JWT token from Authorization header.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials
        Authorization credentials from request header

    Returns
    -------
    TokenData
        Verified token data

    Raises
    ------
    HTTPException
        If token is invalid or expired (401)
    """
    return verify_token(credentials.credentials)


async def get_current_account(
    token_data: Annotated[TokenData, Depends(get_current_token)],
) -> BaseUSMSAccount:
    """Create and initialize USMS account from token data.

    Parameters
    ----------
    token_data : TokenData
        Verified token data with encrypted credentials

    Returns
    -------
    BaseUSMSAccount
        Initialized USMS account (async)

    Raises
    ------
    HTTPException
        If login fails or credentials are invalid (401)
    """
    try:
        # Decrypt password from token
        plain_password = _decrypt_password(token_data.password)

        # Create async account with decrypted credentials
        account = await initialize_usms_account(
            username=token_data.username,
            password=plain_password,
            async_mode=True,
        )

        return account

    except (USMSLoginError, USMSMissingCredentialsError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize account: {e!s}",
        ) from e


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed password.

    Parameters
    ----------
    plain_password : str
        Plain text password
    hashed_password : str
        Bcrypt hashed password

    Returns
    -------
    bool
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt.

    Parameters
    ----------
    password : str
        Plain text password

    Returns
    -------
    str
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


# Type aliases for cleaner endpoint signatures
CurrentToken = Annotated[TokenData, Depends(get_current_token)]
CurrentAccount = Annotated[BaseUSMSAccount, Depends(get_current_account)]


async def get_cache_service():
    """Get cache service instance.

    Returns
    -------
    HybridCache
        Global cache service instance
    """
    from usms.api.services.cache import get_cache

    return get_cache()


CacheService = Annotated["HybridCache", Depends(get_cache_service)]

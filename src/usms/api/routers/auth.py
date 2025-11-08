"""Authentication routes."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from usms import initialize_usms_account
from usms.api.dependencies import (
    CurrentToken,
    create_access_token,
    verify_token,
)
from usms.api.models.auth import (
    LoginRequest,
    TokenResponse,
    TokenVerifyResponse,
)
from usms.exceptions.errors import USMSLoginError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate user and return JWT access token.

    This endpoint validates USMS credentials by attempting to log in to the
    USMS platform. If successful, it returns a JWT token containing the
    encrypted credentials for subsequent API requests.

    Parameters
    ----------
    request : LoginRequest
        Login credentials (username and password)

    Returns
    -------
    TokenResponse
        JWT access token with expiration time

    Raises
    ------
    HTTPException
        401 if credentials are invalid
        500 if USMS platform is unavailable

    Examples
    --------
    ```bash
    curl -X POST "http://localhost:8000/auth/login" \\
        -H "Content-Type: application/json" \\
        -d '{"username": "00-123456", "password": "mypassword"}'
    ```
    """
    try:
        # Validate credentials by attempting to log in
        account = await initialize_usms_account(
            username=request.username, password=request.password, async_mode=True
        )

        # If login successful, create JWT token
        access_token, expires_in = create_access_token(
            username=request.username, password=request.password
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    except USMSLoginError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {e!s}",
        ) from e


@router.get("/verify", response_model=TokenVerifyResponse)
async def verify(token: CurrentToken) -> TokenVerifyResponse:
    """Verify JWT token validity.

    This endpoint checks if a JWT token is valid and not expired.

    Parameters
    ----------
    token : TokenData
        Token data extracted from Authorization header

    Returns
    -------
    TokenVerifyResponse
        Token validity status and expiration info

    Examples
    --------
    ```bash
    curl -X GET "http://localhost:8000/auth/verify" \\
        -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    return TokenVerifyResponse(
        valid=True, user_id=token.user_id, expires_at=token.exp
    )


@router.post("/logout")
async def logout(token: CurrentToken) -> JSONResponse:
    """Logout user (token blacklisting).

    Note: Currently this endpoint doesn't implement actual token blacklisting
    as it would require Redis. Clients should simply discard their tokens.

    Parameters
    ----------
    token : TokenData
        Token data from Authorization header

    Returns
    -------
    JSONResponse
        Success message

    Examples
    --------
    ```bash
    curl -X POST "http://localhost:8000/auth/logout" \\
        -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    # TODO: Implement token blacklist with Redis
    # For now, just return success (client should discard token)
    return JSONResponse(
        content={"message": "Logged out successfully", "user_id": token.user_id}
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token: CurrentToken) -> TokenResponse:
    """Refresh JWT token before expiration.

    This endpoint issues a new token with fresh expiration time.
    The old token should be discarded by the client.

    Parameters
    ----------
    token : TokenData
        Current valid token from Authorization header

    Returns
    -------
    TokenResponse
        New JWT access token

    Examples
    --------
    ```bash
    curl -X POST "http://localhost:8000/auth/refresh" \\
        -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    # Create new token with same credentials
    new_token, expires_in = create_access_token(
        username=token.username, password=token.password
    )

    return TokenResponse(
        access_token=new_token, token_type="bearer", expires_in=expires_in
    )

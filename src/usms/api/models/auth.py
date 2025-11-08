"""Pydantic models for authentication."""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request model for user login.

    Attributes
    ----------
    username : str
        USMS username (IC number)
    password : str
        USMS password
    """

    username: str = Field(..., description="USMS username (IC number)", min_length=1)
    password: str = Field(..., description="USMS password", min_length=1)

    model_config = {"json_schema_extra": {"example": {"username": "00-123456", "password": "mypassword"}}}


class TokenResponse(BaseModel):
    """Response model for successful authentication.

    Attributes
    ----------
    access_token : str
        JWT access token
    token_type : str
        Token type (always "bearer")
    expires_in : int
        Token expiration time in seconds
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
            }
        }
    }


class TokenData(BaseModel):
    """Data extracted from JWT token.

    Attributes
    ----------
    username : str
        USMS username
    password : str
        Encrypted USMS password
    user_id : str
        Hash of username for identification
    exp : datetime
        Token expiration timestamp
    """

    username: str
    password: str  # Encrypted
    user_id: str
    exp: datetime


class TokenVerifyResponse(BaseModel):
    """Response for token verification.

    Attributes
    ----------
    valid : bool
        Whether the token is valid
    user_id : str | None
        User ID if token is valid
    expires_at : datetime | None
        Token expiration time if valid
    """

    valid: bool
    user_id: str | None = None
    expires_at: datetime | None = None

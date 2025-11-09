#!/usr/bin/env python3
"""
Generate a secure JWT secret key for USMS API.

This script generates a cryptographically secure random string suitable for use
as a JWT secret key in production deployments.

Usage:
    python3 scripts/generate_jwt_secret.py

    # Save to file
    python3 scripts/generate_jwt_secret.py > .jwt_secret

    # Copy to clipboard (Linux with xclip)
    python3 scripts/generate_jwt_secret.py | xclip -selection clipboard

    # Use directly in environment
    export USMS_JWT_SECRET=$(python3 scripts/generate_jwt_secret.py)
"""

import secrets


def generate_jwt_secret(length: int = 32) -> str:
    """
    Generate a cryptographically secure JWT secret key.

    Parameters
    ----------
    length : int, optional
        Length of the secret in bytes (default: 32).
        Longer secrets are more secure.

    Returns
    -------
    str
        URL-safe base64-encoded random string.

    Notes
    -----
    - Uses secrets module which is cryptographically strong
    - URL-safe encoding ensures compatibility with environment variables
    - 32 bytes = 256 bits of entropy (recommended minimum)
    - 64 bytes = 512 bits of entropy (high security)
    """
    return secrets.token_urlsafe(length)


def main():
    """Generate and print a JWT secret key."""
    # Generate 32-byte (256-bit) secret by default
    secret = generate_jwt_secret(32)
    print(secret)


if __name__ == "__main__":
    main()

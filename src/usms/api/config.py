"""API configuration from environment variables."""

import os
from functools import lru_cache


class Settings:
    """API configuration settings loaded from environment variables."""

    # Server configuration
    API_HOST: str = os.getenv("USMS_API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("USMS_API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("USMS_API_WORKERS", "1"))
    API_RELOAD: bool = os.getenv("USMS_API_RELOAD", "false").lower() in ("true", "1", "yes")

    # JWT Configuration
    JWT_SECRET: str = os.getenv("USMS_JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = os.getenv("USMS_JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION: int = int(os.getenv("USMS_JWT_EXPIRATION", "86400"))  # 24 hours

    # Redis Configuration
    REDIS_URL: str = os.getenv("USMS_REDIS_URL", "redis://localhost:6379")
    REDIS_DB: int = int(os.getenv("USMS_REDIS_DB", "0"))
    REDIS_PASSWORD: str | None = os.getenv("USMS_REDIS_PASSWORD")

    # Rate Limiting
    RATE_LIMIT: int = int(os.getenv("USMS_API_RATE_LIMIT", "100"))
    RATE_WINDOW: int = int(os.getenv("USMS_API_RATE_WINDOW", "3600"))  # 1 hour

    # Cache TTL (in seconds)
    CACHE_TTL_ACCOUNT: int = int(os.getenv("USMS_CACHE_TTL_ACCOUNT", "900"))  # 15 min
    CACHE_TTL_METER_CURRENT: int = int(os.getenv("USMS_CACHE_TTL_METER_CURRENT", "300"))  # 5 min
    CACHE_TTL_CONSUMPTION: int = int(os.getenv("USMS_CACHE_TTL_CONSUMPTION", "3600"))  # 1 hour

    # Webhook Configuration
    WEBHOOK_TIMEOUT: int = int(os.getenv("USMS_WEBHOOK_TIMEOUT", "10"))
    WEBHOOK_MAX_FAILURES: int = int(os.getenv("USMS_WEBHOOK_MAX_FAILURES", "3"))
    WEBHOOK_DB_PATH: str = os.getenv("USMS_WEBHOOK_DB_PATH", "/data/webhooks.db")

    # Background Jobs
    ENABLE_SCHEDULER: bool = os.getenv("USMS_ENABLE_SCHEDULER", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    FETCH_INTERVAL: int = int(os.getenv("USMS_FETCH_INTERVAL", "15"))  # minutes

    # API Metadata
    API_TITLE: str = "USMS REST API"
    API_DESCRIPTION: str = """
    REST API for accessing Brunei's USMS (Utility Smart Meter System) platform.

    ## Features

    * 🔐 **JWT Authentication** - Secure token-based auth
    * ⚡ **Fast & Async** - Built with FastAPI and async/await
    * 📊 **Consumption Data** - Hourly and daily consumption history
    * 💰 **Cost Calculations** - Calculate costs using Brunei's tariffs
    * 🔔 **Webhooks** - Register webhooks for meter events
    * 🚀 **Rate Limited** - Prevents API abuse
    * 📦 **Redis Caching** - Fast responses with intelligent caching

    ## Installation

    ```bash
    pip install usms[api]
    ```

    ## Usage

    ```bash
    python -m usms serve --host 0.0.0.0 --port 8000
    ```
    """
    API_VERSION: str = "1.0.0"
    API_CONTACT: dict = {
        "name": "USMS Library",
        "url": "https://github.com/azsaurr/usms",
        "email": "102905929+azsaurr@users.noreply.github.com",
    }
    API_LICENSE: dict = {
        "name": "MIT",
        "url": "https://github.com/azsaurr/usms/blob/main/LICENSE",
    }

    def __repr__(self) -> str:
        """Return string representation of settings."""
        return (
            f"Settings(API_HOST={self.API_HOST!r}, API_PORT={self.API_PORT}, "
            f"JWT_SECRET={'***' if self.JWT_SECRET != 'CHANGE_ME_IN_PRODUCTION' else 'DEFAULT'}, "
            f"REDIS_URL={self.REDIS_URL!r})"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns
    -------
    Settings
        Application settings loaded from environment variables.

    Notes
    -----
    This function uses @lru_cache to ensure only one Settings instance
    is created throughout the application lifecycle.
    """
    return Settings()


# Convenience export
settings = get_settings()

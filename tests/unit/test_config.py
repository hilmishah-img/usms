"""Unit tests for configuration settings."""

import os

import pytest

from usms.api.config import Settings, get_settings


class TestSettingsDefaults:
    """Tests for default settings values."""

    def test_default_jwt_secret(self):
        """Test default JWT secret."""
        settings = Settings()
        assert settings.JWT_SECRET == "CHANGE_ME_IN_PRODUCTION"

    def test_default_jwt_expiration(self):
        """Test default JWT expiration."""
        settings = Settings()
        assert settings.JWT_EXPIRATION == 86400  # 24 hours

    def test_default_api_host(self):
        """Test default API host."""
        settings = Settings()
        assert settings.API_HOST == "127.0.0.1"

    def test_default_api_port(self):
        """Test default API port."""
        settings = Settings()
        assert settings.API_PORT == 8000

    def test_default_rate_limit(self):
        """Test default rate limit."""
        settings = Settings()
        assert settings.RATE_LIMIT == 100

    def test_default_rate_window(self):
        """Test default rate window."""
        settings = Settings()
        assert settings.RATE_WINDOW == 3600  # 1 hour

    def test_default_cache_memory_size(self):
        """Test default cache memory size."""
        settings = Settings()
        assert settings.CACHE_MEMORY_SIZE == 1000

    def test_default_enable_scheduler(self):
        """Test default scheduler setting."""
        settings = Settings()
        assert settings.ENABLE_SCHEDULER is True


class TestSettingsFromEnvironment:
    """Tests for loading settings from environment variables."""

    def test_jwt_secret_from_env(self, monkeypatch):
        """Test loading JWT secret from environment."""
        monkeypatch.setenv("USMS_JWT_SECRET", "custom_secret_key")
        settings = Settings()
        assert settings.JWT_SECRET == "custom_secret_key"

    def test_jwt_expiration_from_env(self, monkeypatch):
        """Test loading JWT expiration from environment."""
        monkeypatch.setenv("USMS_JWT_EXPIRATION", "7200")
        settings = Settings()
        assert settings.JWT_EXPIRATION == 7200

    def test_api_host_from_env(self, monkeypatch):
        """Test loading API host from environment."""
        monkeypatch.setenv("USMS_API_HOST", "0.0.0.0")
        settings = Settings()
        assert settings.API_HOST == "0.0.0.0"

    def test_api_port_from_env(self, monkeypatch):
        """Test loading API port from environment."""
        monkeypatch.setenv("USMS_API_PORT", "9000")
        settings = Settings()
        assert settings.API_PORT == 9000

    def test_rate_limit_from_env(self, monkeypatch):
        """Test loading rate limit from environment."""
        monkeypatch.setenv("USMS_API_RATE_LIMIT", "200")
        settings = Settings()
        assert settings.RATE_LIMIT == 200

    def test_rate_window_from_env(self, monkeypatch):
        """Test loading rate window from environment."""
        monkeypatch.setenv("USMS_API_RATE_WINDOW", "7200")
        settings = Settings()
        assert settings.RATE_WINDOW == 7200

    def test_cache_memory_size_from_env(self, monkeypatch):
        """Test loading cache memory size from environment."""
        monkeypatch.setenv("USMS_CACHE_MEMORY_SIZE", "2000")
        settings = Settings()
        assert settings.CACHE_MEMORY_SIZE == 2000

    def test_enable_scheduler_from_env(self, monkeypatch):
        """Test loading scheduler setting from environment."""
        monkeypatch.setenv("USMS_ENABLE_SCHEDULER", "false")
        settings = Settings()
        assert settings.ENABLE_SCHEDULER is False


class TestSettingsSingleton:
    """Tests for settings singleton pattern."""

    def test_get_settings_returns_same_instance(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_settings_cached(self, monkeypatch):
        """Test that settings are cached and not reloaded."""
        # Get initial settings
        settings1 = get_settings()
        initial_secret = settings1.JWT_SECRET

        # Change environment variable
        monkeypatch.setenv("USMS_JWT_SECRET", "new_secret")

        # Get settings again (should be cached, not reloaded)
        settings2 = get_settings()

        # Should still have the initial secret (cached)
        assert settings2.JWT_SECRET == initial_secret


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_jwt_algorithm(self):
        """Test JWT algorithm is set correctly."""
        settings = Settings()
        assert settings.JWT_ALGORITHM == "HS256"

    def test_api_metadata(self):
        """Test API metadata is set correctly."""
        settings = Settings()

        assert settings.API_TITLE == "USMS REST API"
        assert "USMS" in settings.API_DESCRIPTION
        assert settings.API_VERSION == "0.9.2"
        assert settings.API_CONTACT["name"] == "AZ"
        assert settings.API_LICENSE["name"] == "MIT"

    def test_api_workers_default(self):
        """Test default API workers count."""
        settings = Settings()
        assert settings.API_WORKERS == 4

    def test_api_reload_default(self):
        """Test default API reload setting."""
        settings = Settings()
        assert settings.API_RELOAD is False

    def test_webhook_timeout_default(self):
        """Test default webhook timeout."""
        settings = Settings()
        assert settings.WEBHOOK_TIMEOUT == 10

    def test_webhook_max_failures_default(self):
        """Test default webhook max failures."""
        settings = Settings()
        assert settings.WEBHOOK_MAX_FAILURES == 3


class TestBooleanEnvironmentVariables:
    """Tests for boolean environment variable parsing."""

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("", False),
        ],
    )
    def test_boolean_parsing(self, monkeypatch, env_value, expected):
        """Test that boolean environment variables are parsed correctly."""
        monkeypatch.setenv("USMS_ENABLE_SCHEDULER", env_value)
        settings = Settings()
        assert settings.ENABLE_SCHEDULER is expected


class TestIntegerEnvironmentVariables:
    """Tests for integer environment variable parsing."""

    def test_invalid_integer_uses_default(self, monkeypatch):
        """Test that invalid integers fall back to defaults."""
        monkeypatch.setenv("USMS_API_PORT", "invalid")
        settings = Settings()
        # Should use default since conversion fails
        assert isinstance(settings.API_PORT, int)

    def test_negative_port_invalid(self, monkeypatch):
        """Test that negative port numbers are handled."""
        monkeypatch.setenv("USMS_API_PORT", "-1000")
        settings = Settings()
        # Implementation should handle this (validate or use default)
        assert settings.API_PORT != -1000  # Either validated or defaulted

    def test_zero_values(self, monkeypatch):
        """Test that zero values are handled correctly."""
        monkeypatch.setenv("USMS_API_RATE_LIMIT", "0")
        settings = Settings()
        assert settings.RATE_LIMIT == 0  # Zero is valid for unlimited

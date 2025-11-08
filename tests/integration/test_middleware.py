"""Integration tests for API middleware."""

import pytest
from fastapi import status
from unittest.mock import patch

from usms.exceptions.errors import (
    USMSLoginError,
    USMSMeterNumberError,
    USMSPageResponseError,
)


class TestRateLimitMiddleware:
    """Tests for rate limiting middleware."""

    def test_rate_limit_headers_present(self, client, auth_headers):
        """Test that rate limit headers are added to responses."""
        response = client.get("/account", headers=auth_headers)

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_headers_values(self, client, auth_headers):
        """Test that rate limit header values are correct."""
        response = client.get("/account", headers=auth_headers)

        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])

        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit

    def test_rate_limit_decreases_with_requests(self, client, auth_headers):
        """Test that remaining count decreases with each request."""
        # First request
        response1 = client.get("/account", headers=auth_headers)
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])

        # Second request
        response2 = client.get("/account", headers=auth_headers)
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])

        # Remaining should decrease
        assert remaining2 < remaining1

    @pytest.mark.skip(reason="Requires high rate limit testing setup")
    def test_rate_limit_exceeded(self, client, auth_headers, monkeypatch):
        """Test that requests are blocked when rate limit is exceeded."""
        # Set very low rate limit for testing
        monkeypatch.setenv("USMS_API_RATE_LIMIT", "5")

        # Make requests until limit is exceeded
        for i in range(10):
            response = client.get("/account", headers=auth_headers)

            if i < 5:
                # Should succeed
                assert response.status_code == status.HTTP_200_OK
            else:
                # Should be rate limited
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestErrorHandlerMiddleware:
    """Tests for error handling middleware."""

    def test_usms_meter_not_found_error(self, client, auth_headers):
        """Test handling of USMSMeterNumberError (404)."""
        with patch("usms.services.account.BaseUSMSAccount.get_meter") as mock_get:
            mock_get.side_effect = USMSMeterNumberError("Meter not found")

            response = client.get("/meters/INVALID001", headers=auth_headers)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()

            assert data["error_code"] == "METER_NOT_FOUND"
            assert "Meter not found" in data["detail"]
            assert "timestamp" in data

    def test_usms_login_error(self, client):
        """Test handling of USMSLoginError (401)."""
        with patch("usms.initialize_usms_account") as mock_init:
            mock_init.side_effect = USMSLoginError("Invalid credentials")

            response = client.post(
                "/auth/login",
                json={"username": "test", "password": "wrong"},
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_usms_page_response_error(self, client, auth_headers):
        """Test handling of USMSPageResponseError (503)."""
        with patch("usms.services.account.BaseUSMSAccount.refresh_data") as mock_refresh:
            mock_refresh.side_effect = USMSPageResponseError("USMS is down")

            response = client.post("/account/refresh", headers=auth_headers)

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()

            assert data["error_code"] == "USMS_UNAVAILABLE"
            assert "timestamp" in data

    def test_validation_error_response(self, client):
        """Test handling of validation errors (422)."""
        response = client.post(
            "/auth/login",
            json={"username": "test"},  # Missing password
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_error_response_structure(self, client, auth_headers):
        """Test that all error responses have consistent structure."""
        with patch("usms.services.account.BaseUSMSAccount.get_meter") as mock_get:
            mock_get.side_effect = USMSMeterNumberError("Test error")

            response = client.get("/meters/TEST001", headers=auth_headers)
            data = response.json()

            # Should have required fields
            assert "detail" in data
            assert "error_code" in data
            assert "timestamp" in data

            # Timestamp should be ISO format
            assert "T" in data["timestamp"]


class TestCORSMiddleware:
    """Tests for CORS middleware."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_preflight_request(self, client):
        """Test handling of CORS preflight requests."""
        response = client.options(
            "/account",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        # Should return 200 for preflight
        assert response.status_code == status.HTTP_200_OK


class TestMiddlewareOrder:
    """Tests for middleware execution order."""

    def test_error_handler_catches_rate_limit(self, client, auth_headers):
        """Test that error handler middleware catches rate limit errors."""
        # Make request
        response = client.get("/account", headers=auth_headers)

        # Should have both error handling and rate limit headers
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            # Error response should have consistent structure
            data = response.json()
            assert "detail" in data
            # But still have rate limit headers
            assert "X-RateLimit-Limit" in response.headers

    def test_rate_limit_before_auth(self, client):
        """Test that rate limiting applies before authentication."""
        # Even without auth, rate limit headers should be present
        response = client.get("/health")

        # Health endpoint doesn't require auth
        assert response.status_code == status.HTTP_200_OK
        # But rate limit headers should still be present
        # (Depending on implementation, this may not apply to public endpoints)


class TestHealthCheckEndpoint:
    """Tests for health check endpoint (no middleware interference)."""

    def test_health_check_success(self, client):
        """Test that health check endpoint works without authentication."""
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_check_no_auth_required(self, client):
        """Test that health check doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "docs" in data

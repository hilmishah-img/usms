"""Integration tests for authentication endpoints."""

import pytest
from fastapi import status


class TestLoginEndpoint:
    """Tests for POST /auth/login endpoint."""

    def test_login_success(self, client, mock_usms_account, test_username, test_password):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={"username": test_username, "password": test_password},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_missing_username(self, client, test_password):
        """Test login with missing username."""
        response = client.post(
            "/auth/login",
            json={"password": test_password},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_missing_password(self, client, test_username):
        """Test login with missing password."""
        response = client.post(
            "/auth/login",
            json={"username": test_username},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_empty_credentials(self, client):
        """Test login with empty credentials."""
        response = client.post(
            "/auth/login",
            json={"username": "", "password": ""},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_invalid_json(self, client):
        """Test login with invalid JSON."""
        response = client.post(
            "/auth/login",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestVerifyEndpoint:
    """Tests for GET /auth/verify endpoint."""

    def test_verify_valid_token(self, client, auth_headers, test_username):
        """Test verifying a valid token."""
        response = client.get("/auth/verify", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["username"] == test_username
        assert "user_id" in data
        assert "expires_at" in data

    def test_verify_missing_token(self, client):
        """Test verifying without providing token."""
        response = client.get("/auth/verify")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_verify_invalid_token(self, client):
        """Test verifying with invalid token."""
        response = client.get(
            "/auth/verify",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_expired_token(self, client, expired_token):
        """Test verifying with expired token."""
        response = client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogoutEndpoint:
    """Tests for POST /auth/logout endpoint."""

    def test_logout_success(self, client, auth_headers):
        """Test successful logout."""
        response = client.post("/auth/logout", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "message" in data
        assert "logged_out_at" in data

    def test_logout_without_token(self, client):
        """Test logout without token."""
        response = client.post("/auth/logout")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestRefreshEndpoint:
    """Tests for POST /auth/refresh endpoint."""

    def test_refresh_success(self, client, auth_headers, mock_usms_account):
        """Test successful token refresh."""
        response = client.post("/auth/refresh", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data

    def test_refresh_without_token(self, client):
        """Test refresh without token."""
        response = client.post("/auth/refresh")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_refresh_with_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthFlow:
    """Tests for complete authentication flow."""

    def test_complete_auth_flow(self, client, mock_usms_account, test_username, test_password):
        """Test complete auth flow: login -> verify -> logout."""
        # Step 1: Login
        login_response = client.post(
            "/auth/login",
            json={"username": test_username, "password": test_password},
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]

        # Step 2: Verify token
        verify_response = client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert verify_response.status_code == status.HTTP_200_OK

        # Step 3: Logout
        logout_response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_response.status_code == status.HTTP_200_OK

    def test_login_and_use_token(self, client, mock_usms_account, test_username, test_password):
        """Test that token from login can be used for authenticated endpoints."""
        # Login
        login_response = client.post(
            "/auth/login",
            json={"username": test_username, "password": test_password},
        )
        token = login_response.json()["access_token"]

        # Use token to access protected endpoint
        account_response = client.get(
            "/account",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert account_response.status_code == status.HTTP_200_OK

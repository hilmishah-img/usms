"""Unit tests for Pydantic models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from usms.api.models.account import AccountResponse, RefreshResponse
from usms.api.models.auth import LoginRequest, TokenData, TokenResponse
from usms.api.models.consumption import ConsumptionDataPoint, ConsumptionResponse
from usms.api.models.meter import MeterCreditResponse, MeterResponse, MeterUnitResponse


class TestAuthModels:
    """Tests for authentication models."""

    def test_login_request_valid(self):
        """Test creating a valid LoginRequest."""
        data = {"username": "00-123456", "password": "test_password"}
        request = LoginRequest(**data)

        assert request.username == "00-123456"
        assert request.password == "test_password"

    def test_login_request_missing_username(self):
        """Test that LoginRequest requires username."""
        with pytest.raises(ValidationError):
            LoginRequest(password="test_password")

    def test_login_request_missing_password(self):
        """Test that LoginRequest requires password."""
        with pytest.raises(ValidationError):
            LoginRequest(username="00-123456")

    def test_token_response_valid(self):
        """Test creating a valid TokenResponse."""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 86400,
        }
        response = TokenResponse(**data)

        assert response.access_token.startswith("eyJ")
        assert response.token_type == "bearer"
        assert response.expires_in == 86400

    def test_token_data_valid(self, test_username):
        """Test creating valid TokenData."""
        data = {
            "username": test_username,
            "password": "encrypted_password",
            "user_id": "abc123",
            "exp": datetime.now(timezone.utc),
        }
        token_data = TokenData(**data)

        assert token_data.username == test_username
        assert token_data.password == "encrypted_password"
        assert token_data.user_id == "abc123"
        assert isinstance(token_data.exp, datetime)


class TestAccountModels:
    """Tests for account models."""

    def test_meter_response_valid(self):
        """Test creating MeterResponse with all required fields."""
        now = datetime.now(timezone.utc)
        data = {
            "no": "TEST001",
            "id": "base64id",
            "type": "Electricity",
            "unit": "kWh",
            "remaining_unit": 100.5,
            "remaining_credit": 50.25,
            "last_update": now.isoformat(),
            "status": "ACTIVE",
            "is_active": True,
            "address": "123 Test St",
            "kampong": "Kg Test",
            "mukim": "Mukim Test",
            "district": "Test District",
            "postcode": "TE1234",
        }
        meter = MeterResponse(**data)

        assert meter.no == "TEST001"
        assert meter.type == "Electricity"
        assert meter.unit == "kWh"
        assert meter.remaining_unit == 100.5

    def test_account_response_valid(self):
        """Test creating valid AccountResponse."""
        now = datetime.now(timezone.utc)
        data = {
            "name": "Test User",
            "reg_no": "00-123456",
            "meters": [
                {
                    "no": "TEST001",
                    "id": "base64id",
                    "type": "Electricity",
                    "unit": "kWh",
                    "remaining_unit": 100.5,
                    "remaining_credit": 50.25,
                    "last_update": now.isoformat(),
                    "status": "ACTIVE",
                    "is_active": True,
                    "address": "123 Test St",
                    "kampong": "Kg Test",
                    "mukim": "Mukim Test",
                    "district": "Test District",
                    "postcode": "TE1234",
                }
            ],
            "last_refresh": now.isoformat(),
        }
        response = AccountResponse(**data)

        assert response.name == "Test User"
        assert response.reg_no == "00-123456"
        assert len(response.meters) == 1
        assert response.meters[0].no == "TEST001"

    def test_account_response_empty_meters(self):
        """Test AccountResponse with no meters."""
        data = {
            "name": "Test User",
            "reg_no": "00-123456",
            "meters": [],
        }
        response = AccountResponse(**data)

        assert len(response.meters) == 0

    def test_refresh_response_valid(self):
        """Test creating valid RefreshResponse."""
        data = {
            "message": "Account refreshed successfully",
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
        }
        response = RefreshResponse(**data)

        assert response.message == "Account refreshed successfully"
        assert response.refreshed_at is not None


class TestMeterModels:
    """Tests for meter models."""

    def test_meter_unit_response_valid(self):
        """Test creating valid MeterUnitResponse."""
        now = datetime.now(timezone.utc)
        data = {
            "meter_no": "TEST001",
            "remaining_unit": 100.5,
            "unit": "kWh",
            "last_update": now.isoformat(),
        }
        response = MeterUnitResponse(**data)

        assert response.meter_no == "TEST001"
        assert response.remaining_unit == 100.5
        assert response.unit == "kWh"

    def test_meter_credit_response_valid(self):
        """Test creating valid MeterCreditResponse."""
        now = datetime.now(timezone.utc)
        data = {
            "meter_no": "TEST001",
            "remaining_credit": 50.25,
            "currency": "BND",
            "last_update": now.isoformat(),
        }
        response = MeterCreditResponse(**data)

        assert response.meter_no == "TEST001"
        assert response.remaining_credit == 50.25
        assert response.currency == "BND"


class TestConsumptionModels:
    """Tests for consumption models."""

    def test_consumption_data_point_valid(self):
        """Test creating valid ConsumptionDataPoint."""
        now = datetime.now(timezone.utc)
        data = {"timestamp": now.isoformat(), "consumption": 10.5, "cost": 5.25}
        point = ConsumptionDataPoint(**data)

        assert isinstance(point.timestamp, str)
        assert point.consumption == 10.5
        assert point.cost == 5.25

    def test_consumption_data_point_optional_cost(self):
        """Test ConsumptionDataPoint with optional cost."""
        now = datetime.now(timezone.utc)
        data = {"timestamp": now.isoformat(), "consumption": 10.5}
        point = ConsumptionDataPoint(**data)

        assert point.consumption == 10.5
        assert point.cost is None

    def test_consumption_response_valid(self, sample_consumption_data):
        """Test creating valid ConsumptionResponse."""
        data = {
            "meter_no": "TEST001",
            "data": [
                {
                    "timestamp": point["timestamp"].isoformat(),
                    "consumption": point["consumption"],
                    "cost": point["cost"],
                }
                for point in sample_consumption_data
            ],
            "total_consumption": sum(p["consumption"] for p in sample_consumption_data),
            "total_cost": sum(p["cost"] for p in sample_consumption_data),
        }
        response = ConsumptionResponse(**data)

        assert response.meter_no == "TEST001"
        assert len(response.data) == len(sample_consumption_data)
        assert response.total_consumption > 0
        assert response.total_cost > 0

    def test_consumption_response_empty_data(self):
        """Test ConsumptionResponse with empty data."""
        data = {
            "meter_no": "TEST001",
            "data": [],
            "total_consumption": 0.0,
            "total_cost": 0.0,
        }
        response = ConsumptionResponse(**data)

        assert len(response.data) == 0
        assert response.total_consumption == 0.0
        assert response.total_cost == 0.0

    def test_consumption_response_optional_cost(self):
        """Test ConsumptionResponse with optional total_cost."""
        data = {
            "meter_no": "TEST001",
            "data": [
                {"timestamp": datetime.now(timezone.utc).isoformat(), "consumption": 10.5}
            ],
            "total_consumption": 10.5,
        }
        response = ConsumptionResponse(**data)

        assert response.total_consumption == 10.5
        assert response.total_cost is None


class TestModelValidation:
    """Tests for model validation rules."""

    def test_negative_consumption_invalid(self):
        """Test that negative consumption values are invalid."""
        with pytest.raises(ValidationError):
            ConsumptionDataPoint(
                timestamp=datetime.now(timezone.utc).isoformat(),
                consumption=-10.5,
            )

    def test_negative_credit_invalid(self):
        """Test that negative credit values are invalid."""
        with pytest.raises(ValidationError):
            MeterCreditResponse(meter_no="TEST001", remaining_credit=-50.0)

    def test_empty_meter_no_invalid(self):
        """Test that empty meter_no is invalid."""
        with pytest.raises(ValidationError):
            MeterResponse(
                meter_no="",
                meter_type="Electricity",
                address="123 Test St",
                remaining_unit=100.5,
                remaining_credit=50.25,
                unit="kWh",
            )

    def test_empty_username_invalid(self):
        """Test that empty username is invalid."""
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="test_password")


class TestModelSerialization:
    """Tests for model JSON serialization."""

    def test_account_response_serialization(self):
        """Test that AccountResponse can be serialized to JSON."""
        data = {
            "name": "Test User",
            "reg_no": "00-123456",
            "meters": [
                {
                    "meter_no": "TEST001",
                    "meter_type": "Electricity",
                    "address": "123 Test St",
                }
            ],
            "is_initialized": True,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }
        response = AccountResponse(**data)

        # Should be able to convert to dict
        json_data = response.model_dump()
        assert isinstance(json_data, dict)
        assert json_data["name"] == "Test User"
        assert json_data["reg_no"] == "00-123456"

    def test_consumption_response_serialization(self):
        """Test that ConsumptionResponse can be serialized to JSON."""
        now = datetime.now(timezone.utc)
        data = {
            "meter_no": "TEST001",
            "data": [{"timestamp": now.isoformat(), "consumption": 10.5, "cost": 5.25}],
            "total_consumption": 10.5,
            "total_cost": 5.25,
        }
        response = ConsumptionResponse(**data)

        json_data = response.model_dump()
        assert isinstance(json_data, dict)
        assert json_data["meter_no"] == "TEST001"
        assert len(json_data["data"]) == 1

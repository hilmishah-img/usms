"""Shared pytest fixtures for USMS tests."""

import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


# API Test Fixtures
@pytest.fixture
def app():
    """Create FastAPI app for testing.

    Returns
    -------
    FastAPI
        Test FastAPI application instance
    """
    from usms.api.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    """Create test client for API testing.

    Parameters
    ----------
    app : FastAPI
        FastAPI application instance

    Returns
    -------
    TestClient
        FastAPI test client
    """
    return TestClient(app)


@pytest.fixture
def test_username():
    """Test USMS username.

    Returns
    -------
    str
        Mock IC number for testing
    """
    return "00-123456"


@pytest.fixture
def test_password():
    """Test USMS password.

    Returns
    -------
    str
        Mock password for testing
    """
    return "test_password_123"


@pytest.fixture
def valid_token(test_username, test_password):
    """Create valid JWT token for testing.

    Parameters
    ----------
    test_username : str
        Test username
    test_password : str
        Test password

    Returns
    -------
    tuple[str, int]
        Tuple of (access_token, expires_in)
    """
    from usms.api.dependencies import create_access_token

    return create_access_token(test_username, test_password)


@pytest.fixture
def auth_headers(valid_token):
    """Create authentication headers with valid token.

    Parameters
    ----------
    valid_token : tuple[str, int]
        Valid token and expiration

    Returns
    -------
    dict
        Authorization headers
    """
    token, _ = valid_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def expired_token(test_username, test_password):
    """Create expired JWT token for testing.

    Parameters
    ----------
    test_username : str
        Test username
    test_password : str
        Test password

    Returns
    -------
    str
        Expired JWT token
    """
    from jose import jwt

    from usms.api.config import get_settings
    from usms.api.dependencies import _encrypt_password

    settings = get_settings()

    # Create token that expired 1 hour ago
    import hashlib

    user_id = hashlib.sha256(test_username.encode()).hexdigest()[:16]
    encrypted_password = _encrypt_password(test_password)
    expire = datetime.now(timezone.utc) - timedelta(hours=1)

    token_data = {
        "sub": user_id,
        "username": test_username,
        "password": encrypted_password,
        "exp": expire,
    }

    return jwt.encode(token_data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# Cache Test Fixtures
@pytest.fixture
def test_cache():
    """Create isolated cache instance for testing.

    Yields
    ------
    HybridCache
        Isolated cache instance with temporary disk storage
    """
    from usms.api.services.cache import HybridCache

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = HybridCache(memory_size=100, disk_path=tmpdir)
        yield cache
        cache.close()


# Database Test Fixtures
@pytest.fixture
def test_db():
    """Create isolated test database.

    Yields
    ------
    Database
        Isolated database instance with temporary file
    """
    from usms.api.database import Database

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = Database(db_path=f.name)
        yield db
        # Cleanup handled by tempfile


# Mock USMS Service Fixtures
@pytest.fixture
def mock_meter():
    """Create mock USMS meter.

    Returns
    -------
    MagicMock
        Mock meter object
    """
    meter = MagicMock()
    meter.no = "TEST001"
    meter.type = "Electricity"
    meter.address = "Test Address"
    meter.remaining_unit = 100.5
    meter.remaining_credit = 50.25
    meter.unit = "kWh"
    return meter


@pytest.fixture
def mock_account(mock_meter):
    """Create mock USMS account.

    Parameters
    ----------
    mock_meter : MagicMock
        Mock meter

    Returns
    -------
    AsyncMock
        Mock account object with async methods
    """
    account = AsyncMock()
    account.name = "Test User"
    account.reg_no = "00-123456"
    account.meters = [mock_meter]
    account.get_meter.return_value = mock_meter
    account.refresh_data = AsyncMock(return_value=None)
    account.is_initialized = True
    account.last_update = datetime.now(timezone.utc)
    return account


@pytest.fixture
def mock_usms_account(monkeypatch, mock_account):
    """Mock initialize_usms_account function.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture
    mock_account : AsyncMock
        Mock account object

    Returns
    -------
    AsyncMock
        Mocked initialize function
    """

    async def mock_initialize(*args, **kwargs):
        return mock_account

    monkeypatch.setattr("usms.api.dependencies.initialize_usms_account", mock_initialize)
    return mock_account


# Scheduler Test Fixtures
@pytest.fixture
def test_scheduler():
    """Create test scheduler instance.

    Yields
    ------
    SchedulerService
        Scheduler instance (not started)
    """
    from usms.api.services.scheduler import SchedulerService

    scheduler = SchedulerService()
    yield scheduler
    # Ensure cleanup
    if scheduler.scheduler.running:
        scheduler.shutdown()


# Settings Test Fixtures
@pytest.fixture
def test_settings(monkeypatch):
    """Create test settings with overridden environment variables.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture

    Yields
    ------
    Settings
        Test settings instance
    """
    # Set test environment variables
    monkeypatch.setenv("USMS_JWT_SECRET", "test_secret_key_for_testing_only")
    monkeypatch.setenv("USMS_API_RATE_LIMIT", "1000")
    monkeypatch.setenv("USMS_ENABLE_SCHEDULER", "false")

    from usms.api.config import Settings

    yield Settings()


# Consumption Data Fixtures
@pytest.fixture
def sample_consumption_data():
    """Create sample consumption data for testing.

    Returns
    -------
    list[dict]
        List of consumption data points
    """
    return [
        {
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=i),
            "consumption": 10.0 + i,
            "cost": 5.0 + i * 0.5,
        }
        for i in range(24)
    ]


# Tariff Test Fixtures
@pytest.fixture
def electricity_tariff():
    """Get electricity tariff instance.

    Returns
    -------
    ElectricityTariff
        Electricity tariff instance
    """
    from usms.models.tariff import ElectricityTariff

    return ElectricityTariff()


@pytest.fixture
def water_tariff():
    """Get water tariff instance.

    Returns
    -------
    WaterTariff
        Water tariff instance
    """
    from usms.models.tariff import WaterTariff

    return WaterTariff()

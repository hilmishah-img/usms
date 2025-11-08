# USMS API Testing Guide

This document provides comprehensive information about the test suite for the USMS API.

## Test Suite Overview

### What Was Fixed

1. **Critical Authentication Bug** - Fixed password encryption issue in `src/usms/api/dependencies.py`:
   - Previously: Password was hashed with bcrypt (one-way) and stored in JWT
   - Problem: Cannot decrypt bcrypt hash to authenticate with USMS
   - Solution: Implemented reversible encryption using Fernet from cryptography library
   - Impact: JWT tokens now properly encrypt/decrypt passwords for USMS authentication

### Test Structure

```
tests/
├── conftest.py                 # Shared fixtures (TestClient, mocks, test data)
├── test_import.py              # ✓ Existing: Basic import tests
├── test_tariff.py              # ✓ Existing: Tariff calculation tests
│
├── unit/                       # Unit tests (no external dependencies)
│   ├── test_auth.py            # ✓ NEW: JWT, password encryption/decryption (15 tests)
│   ├── test_cache.py           # ✓ NEW: HybridCache L1/L2 operations (30+ tests)
│   ├── test_models.py          # ✓ NEW: Pydantic model validation (25+ tests)
│   └── test_config.py          # ✓ NEW: Settings and environment variables (20+ tests)
│
└── integration/                # Integration tests (with mocks)
    ├── test_auth_endpoints.py  # ✓ NEW: Authentication endpoints (15+ tests)
    └── test_middleware.py      # ✓ NEW: Middleware (rate limit, errors) (15+ tests)
```

### Test Statistics

- **Total Test Files**: 9
- **Total Tests**: ~120 tests
- **Code Coverage Target**: >80%

## Running Tests

### Prerequisites

1. **Install dependencies**:
   ```sh
   # Using uv (recommended)
   uv sync --all-extras

   # OR using pip
   pip install -e ".[api]"
   pip install pytest pytest-asyncio pytest-mock freezegun
   ```

2. **Ensure you have Python 3.10+**:
   ```sh
   python --version  # Should be 3.10 or higher
   ```

### Running All Tests

```sh
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src/usms --cov-report=html --cov-report=term

# Using Poe the Poet (recommended)
poe test
```

### Running Specific Tests

```sh
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_auth.py

# Run specific test
pytest tests/unit/test_auth.py::TestPasswordEncryption::test_encrypt_decrypt_password

# Run tests matching pattern
pytest -k "auth"
```

### Running Tests in Parallel

```sh
# Run tests in parallel (faster)
pytest -n auto
```

## Test Coverage

### Generating Coverage Reports

```sh
# Generate HTML coverage report
pytest --cov=src/usms --cov-report=html
# Open reports/htmlcov/index.html in browser

# Generate XML coverage report
pytest --cov=src/usms --cov-report=xml
# Output: reports/coverage.xml

# Terminal coverage report
pytest --cov=src/usms --cov-report=term-missing
```

### Coverage by Module

Expected coverage for each module:

| Module | Target Coverage | Tests |
|--------|----------------|-------|
| `api/dependencies.py` | 95% | test_auth.py |
| `api/services/cache.py` | 90% | test_cache.py |
| `api/models/*` | 100% | test_models.py |
| `api/config.py` | 95% | test_config.py |
| `api/routers/auth.py` | 85% | test_auth_endpoints.py |
| `api/middleware/*` | 80% | test_middleware.py |

## Test Details

### Unit Tests

#### test_auth.py - Authentication & JWT
- **Password Encryption**: Tests Fernet encryption/decryption
- **Password Hashing**: Tests bcrypt hashing for future use
- **Token Creation**: Tests JWT token generation with encrypted credentials
- **Token Verification**: Tests token validation, expiration, signature verification
- **Token Data Extraction**: Tests decrypting password from token payload

Key test scenarios:
- ✓ Encrypt and decrypt passwords correctly
- ✓ Different passwords produce different encrypted outputs
- ✓ Invalid encrypted data raises errors
- ✓ Tokens contain encrypted (not plain) passwords
- ✓ Expired tokens are rejected
- ✓ Invalid signatures are rejected
- ✓ Tokens with missing fields are rejected

#### test_cache.py - Hybrid Cache
- **Basic Operations**: Set, get, clear operations
- **TTL Management**: L1 and L2 expiration handling
- **Cache Layers**: L1 (memory) and L2 (disk) interactions
- **Invalidation**: Exact key and pattern-based invalidation
- **Statistics**: Hit/miss tracking, cache sizes
- **Cleanup**: Expired entry removal
- **Edge Cases**: None values, empty strings, large objects, datetime objects

Key test scenarios:
- ✓ L1 cache expires and falls back to L2
- ✓ L2 hits are promoted to L1
- ✓ Pattern invalidation (e.g., "meter:123:*")
- ✓ Hit rate calculation
- ✓ Statistics tracking
- ✓ Cleanup preserves valid entries

#### test_models.py - Pydantic Models
- **Auth Models**: LoginRequest, TokenResponse, TokenData
- **Account Models**: AccountResponse, MeterInfo, RefreshResponse
- **Meter Models**: MeterResponse, MeterUnitResponse, MeterCreditResponse
- **Consumption Models**: ConsumptionDataPoint, ConsumptionResponse
- **Validation**: Field requirements, type checking, value constraints
- **Serialization**: JSON conversion, datetime handling

Key test scenarios:
- ✓ Valid model creation
- ✓ Missing required fields raise ValidationError
- ✓ Negative values are rejected where appropriate
- ✓ Empty strings are rejected for required fields
- ✓ Models serialize to JSON correctly

#### test_config.py - Configuration
- **Default Values**: All settings have proper defaults
- **Environment Variables**: Settings load from USMS_* env vars
- **Singleton Pattern**: get_settings() returns cached instance
- **Boolean Parsing**: true/false/1/0/yes/no parsed correctly
- **Integer Parsing**: Invalid integers handled gracefully
- **Metadata**: API title, version, contact info

Key test scenarios:
- ✓ Default JWT secret is "CHANGE_ME_IN_PRODUCTION"
- ✓ Environment variables override defaults
- ✓ get_settings() returns same instance (cached)
- ✓ Boolean environment variables parsed correctly
- ✓ Invalid integers use defaults

### Integration Tests

#### test_auth_endpoints.py - Authentication Endpoints
- **POST /auth/login**: Login with credentials, get JWT token
- **GET /auth/verify**: Verify token validity
- **POST /auth/logout**: Logout
- **POST /auth/refresh**: Refresh token
- **Auth Flow**: Complete login → verify → logout flow

Key test scenarios:
- ✓ Successful login returns access_token
- ✓ Missing username/password returns 422
- ✓ Valid token verification returns user data
- ✓ Missing/invalid/expired tokens return 401
- ✓ Complete auth flow works end-to-end
- ✓ Token from login can access protected endpoints

#### test_middleware.py - Middleware
- **Rate Limiting**: Request counting, limit enforcement, headers
- **Error Handling**: USMS exceptions → HTTP status codes
- **CORS**: Cross-origin headers, preflight requests
- **Health Check**: Public endpoint without auth

Key test scenarios:
- ✓ Rate limit headers present in responses
- ✓ Remaining count decreases with requests
- ✓ USMSMeterNumberError → 404 with error_code
- ✓ USMSLoginError → 401
- ✓ USMSPageResponseError → 503
- ✓ Consistent error response structure
- ✓ CORS headers present
- ✓ Health check works without auth

## Fixtures

### Test Data Fixtures
- `test_username`: Mock IC number (00-123456)
- `test_password`: Mock password
- `valid_token`: Valid JWT token
- `expired_token`: Expired JWT token for testing
- `auth_headers`: Authorization headers with Bearer token
- `sample_consumption_data`: 24 hours of consumption data

### Mock Fixtures
- `mock_meter`: Mock USMS meter object
- `mock_account`: Mock USMS account with async methods
- `mock_usms_account`: Mocked initialize_usms_account function

### Service Fixtures
- `test_cache`: Isolated HybridCache with temp directory
- `test_db`: Isolated Database with temp file
- `test_scheduler`: SchedulerService instance
- `test_settings`: Settings with overridden env vars

### API Fixtures
- `app`: FastAPI application instance
- `client`: FastAPI TestClient for making requests

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[api]"
          pip install pytest pytest-asyncio pytest-mock pytest-cov

      - name: Run tests
        run: pytest --cov=src/usms --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./reports/coverage.xml
```

## Troubleshooting

### Common Issues

#### ImportError: No module named 'usms'
```sh
# Install package in editable mode
pip install -e .
```

#### ImportError: No module named 'pytest_asyncio'
```sh
# Install test dependencies
pip install pytest-asyncio pytest-mock freezegun
```

#### Tests fail with "externally-managed-environment"
```sh
# Create and use virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[api]"
```

#### Fernet encryption errors
```sh
# Ensure cryptography is installed (included in python-jose[cryptography])
pip install "python-jose[cryptography]"
```

#### Tests pass but coverage is low
```sh
# Run with coverage and check what's missing
pytest --cov=src/usms --cov-report=term-missing
# Look at "Missing" column to see uncovered lines
```

## Next Steps

### Additional Tests to Consider

1. **Database Tests** (`tests/unit/test_database.py`):
   - Webhook CRUD operations
   - Database initialization
   - Connection pooling

2. **Scheduler Tests** (`tests/unit/test_scheduler.py`):
   - Job registration
   - Job execution
   - Graceful shutdown

3. **Account Endpoints** (`tests/integration/test_account_endpoints.py`):
   - GET /account
   - POST /account/refresh
   - Cache integration

4. **Meter Endpoints** (`tests/integration/test_meter_endpoints.py`):
   - GET /meters/{id}
   - GET /meters/{id}/unit
   - GET /meters/{id}/credit
   - GET /meters/{id}/consumption/*

5. **End-to-End Tests** (`tests/e2e/test_user_flows.py`):
   - Complete user journeys
   - Real USMS integration (with test account)

### Performance Testing

```python
# tests/performance/test_load.py
import pytest
from locust import HttpUser, task, between

class USMSUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_account(self):
        self.client.get("/account", headers=self.auth_headers)
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

## Summary

This test suite provides comprehensive coverage for the USMS API:
- ✅ Critical authentication bug fixed
- ✅ 120+ tests covering unit and integration scenarios
- ✅ All major API components tested
- ✅ Mocked dependencies for isolated testing
- ✅ No real USMS credentials required
- ✅ Ready for CI/CD integration

To run the tests and verify everything works:
```sh
uv sync --all-extras
poe test
```

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**USMS** is an unofficial Python library providing programmatic access to Brunei's USMS (Utility Smart Meter System) platform. It enables developers to:
- Authenticate and interface with USMS accounts
- Retrieve real-time electricity and water meter information
- Fetch historical consumption data (hourly/daily)
- Calculate costs using Brunei's utility tariffs
- Store consumption data locally (SQLite or CSV)

Available as both a Python package and CLI tool, with full sync/async support.

## Technology Stack

- **Python**: 3.10+ (requires <4.0)
- **Package Manager**: uv (modern replacement for pip/poetry)
- **Build System**: Hatchling
- **HTTP Client**: httpx with HTTP/2 support
- **Data Processing**: pandas
- **Testing**: pytest (with coverage, mock, xdist, typeguard)
- **Linting/Formatting**: ruff (replaces black, flake8, isort)
- **Task Runner**: Poe the Poet
- **Versioning**: Commitizen (Conventional Commits)
- **Documentation**: pdoc
- **Development Environments**: Dev Containers (primary), Codespaces, Nix flakes

## Development Commands

### Setup
```sh
# Create virtual environment and install dependencies
uv sync --python 3.10 --all-extras

# Activate virtual environment
source .venv/bin/activate

# Install pre-commit hooks
pre-commit install --install-hooks
```

### Task Runner (recommended)
```sh
poe            # List all available tasks
poe lint       # Run pre-commit checks
poe test       # Run tests with coverage
poe docs       # Generate documentation
```

### Direct Commands
```sh
# Dependency management
uv add {package}              # Add runtime dependency
uv add --dev {package}        # Add dev dependency
uv sync --upgrade             # Upgrade all dependencies

# Testing
pytest                        # Run all tests
pytest -k test_name          # Run specific test

# Code quality
pre-commit run --all-files   # Run all pre-commit hooks
ruff check --fix             # Lint with auto-fix
ruff format                  # Format code

# Versioning
cz bump                      # Bump version and update CHANGELOG
git push origin main --tags  # Push with tags
```

### CLI Usage
```sh
# Basic usage
python -m usms -u <username> -p <password> -m <meter> --unit

# List all meters
python -m usms -u <username> -p <password> --list

# Use environment variables
export USMS_USERNAME="<ic_number>"
export USMS_PASSWORD="<password>"
python -m usms -m <meter> --credit

# Synchronous mode (default is async)
python -m usms --sync -m <meter> --unit
```

### Docker Deployment

```sh
# Pull from GitHub Container Registry
docker pull ghcr.io/azsaurr/usms:latest

# Run with environment variables
docker run --rm \
  -e USMS_USERNAME="<ic_number>" \
  -e USMS_PASSWORD="<password>" \
  ghcr.io/azsaurr/usms:latest -m <meter> --unit

# Use docker-compose with profiles
docker-compose -f docker-compose.prod.yml --profile unit up

# Build production image locally
docker build --target runtime -t usms:local .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 --target runtime -t usms .
```

**Docker Image Details:**
- **Registry**: GitHub Container Registry (GHCR)
- **Image**: `ghcr.io/azsaurr/usms`
- **Tags**: `latest`, `vX.Y.Z`, `X.Y`, `X`
- **Platforms**: linux/amd64, linux/arm64
- **Base**: Python 3.10 slim-bookworm
- **Entry point**: `python -m usms`
- **Volume**: `/data` (for SQLite/CSV persistence)
- **User**: Non-root (UID 1000)
- **Multi-stage build**: Builder + Runtime stages
- **Automated publishing**: On git tag push (via GitHub Actions)

## REST API Development

### API Overview

The USMS library includes a production-ready REST API built with FastAPI that exposes all library functionality via HTTP endpoints. The API features:

- **JWT Authentication**: Token-based auth with encrypted credentials stored in JWT payload
- **Rate Limiting**: Sliding window algorithm with configurable limits per user
- **Hybrid Caching**: Two-tier cache (L1: in-memory TTLCache, L2: SQLite-backed diskcache)
- **Background Jobs**: APScheduler for cache cleanup and maintenance
- **Error Handling**: Consistent error responses for all USMS exceptions
- **Auto-generated Docs**: Interactive Swagger UI and ReDoc documentation

### API Technology Stack

Additional dependencies for API mode (installed via `pip install usms[api]`):

- **FastAPI**: Modern async web framework
- **Uvicorn**: ASGI server with uvloop and httptools
- **Pydantic**: Data validation and serialization
- **python-jose**: JWT token generation and verification with cryptography
- **cachetools**: In-memory TTL cache (L1 cache layer)
- **diskcache**: SQLite-backed persistent cache (L2 cache layer)
- **APScheduler**: Background job scheduler for maintenance tasks
- **aiosqlite**: Async SQLite for webhook storage

### Running the API Server

```sh
# Install with API dependencies
uv sync --all-extras

# Development mode (auto-reload, single worker)
python -m usms serve --reload

# Production mode (multiple workers)
python -m usms serve --host 0.0.0.0 --port 8000 --workers 4

# Using Docker
docker-compose -f docker-compose.prod.yml --profile api up -d

# Development with Docker
docker-compose -f docker-compose.prod.yml --profile api-dev up
```

Access interactive docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API Architecture

The API layer is organized separately from the core library:

```
src/usms/
├── api/
│   ├── main.py              # FastAPI app with lifespan management
│   ├── config.py            # Environment-based settings
│   ├── dependencies.py      # JWT auth and DI setup
│   ├── database.py          # SQLite for webhooks (future)
│   ├── models/              # Pydantic models for API
│   │   ├── auth.py          # LoginRequest, TokenResponse, TokenData
│   │   ├── account.py       # AccountResponse, RefreshResponse
│   │   ├── meter.py         # MeterResponse, Unit/Credit/Status responses
│   │   └── consumption.py   # ConsumptionResponse, CostCalculation
│   ├── routers/             # FastAPI route handlers
│   │   ├── auth.py          # POST /auth/login, /verify, /refresh, /logout
│   │   ├── account.py       # GET /account, POST /account/refresh
│   │   ├── meters.py        # GET /meters/{id}/unit, /credit, /consumption
│   │   └── tariffs.py       # GET /tariffs/electricity, /water
│   ├── middleware/          # Custom middleware
│   │   ├── error_handler.py # USMS exception → HTTP error responses
│   │   └── rate_limit.py    # Sliding window rate limiting
│   └── services/            # API-specific services
│       ├── cache.py         # HybridCache (L1 + L2)
│       └── scheduler.py     # Background jobs (cache cleanup)
└── cli.py                   # Added 'serve' subcommand
```

### Key Components

#### 1. JWT Authentication (`api/dependencies.py`)

```python
# Token creation with encrypted credentials
def create_access_token(username: str, password: str) -> tuple[str, int]:
    # Credentials encrypted and stored in JWT payload
    # Token signed with USMS_JWT_SECRET
    # Expires after USMS_JWT_EXPIRATION seconds (default: 24h)

# Token verification
def verify_token(token: str) -> TokenData:
    # Verifies JWT signature
    # Checks expiration
    # Decrypts credentials from payload

# Dependency injection
async def get_current_account(token_data: TokenData) -> BaseUSMSAccount:
    # Initializes USMS account using credentials from token
    # Returns authenticated account instance
    # Cached per request
```

**Security Note**: In production, consider storing only username in JWT and using secure credential storage (e.g., vault, encrypted database) for passwords. Current implementation encrypts passwords in JWT payload for simplicity.

#### 2. Hybrid Caching (`api/services/cache.py`)

Two-tier caching strategy for optimal performance:

```python
class HybridCache:
    # L1: In-memory cache (cachetools TTLCache)
    # - Fast access (nanoseconds)
    # - Limited size (default: 1000 items)
    # - Short TTL (default: 15 minutes)
    # - Lost on restart

    # L2: Disk cache (diskcache backed by SQLite)
    # - Persistent across restarts
    # - Larger capacity
    # - Longer TTL (default: 1 hour)
    # - Automatic eviction when full

    def get(self, key: str) -> Any | None:
        # Check L1 → L2 → None
        # Promote L2 hits to L1

    def set(self, key: str, value: Any, ttl_memory: int, ttl_disk: int):
        # Write to both L1 and L2 with different TTLs

    def invalidate(self, pattern: str | None, exact_key: str | None):
        # Pattern matching for invalidation (e.g., "meter:123:*")
        # Clears from both L1 and L2
```

**Cache Keys Pattern**:
- Account: `account:{reg_no}`
- Meter info: `meter:{meter_no}:info`
- Meter unit: `meter:{meter_no}:unit`
- Meter credit: `meter:{meter_no}:credit`
- Consumption: `meter:{meter_no}:consumption:{type}:{days}`

#### 3. Rate Limiting (`api/middleware/rate_limit.py`)

```python
class RateLimitMiddleware:
    # Uses cachetools.TTLCache for request tracking
    # Sliding window algorithm
    # Per-user limits (extracted from JWT)
    # Returns 429 Too Many Requests when exceeded
    # Adds headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
```

**Configuration**:
- `USMS_API_RATE_LIMIT`: Max requests per window (default: 100)
- `USMS_API_RATE_WINDOW`: Window size in seconds (default: 3600 = 1 hour)

#### 4. Error Handler (`api/middleware/error_handler.py`)

Maps USMS exceptions to HTTP status codes:

| Exception | HTTP Status | Error Code |
|-----------|-------------|------------|
| `USMSMeterNumberError` | 404 | `METER_NOT_FOUND` |
| `USMSLoginError` | 401 | `AUTHENTICATION_FAILED` |
| `USMSMissingCredentialsError` | 400 | `MISSING_CREDENTIALS` |
| `USMSNotInitializedError` | 500 | `SERVICE_NOT_INITIALIZED` |
| `USMSFutureDateError` | 400 | `INVALID_DATE` |
| `USMSConsumptionHistoryNotFoundError` | 404 | `DATA_NOT_FOUND` |
| `USMSPageResponseError` | 503 | `USMS_UNAVAILABLE` |

All errors return consistent JSON:
```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-01-08T12:34:56.789Z"
}
```

#### 5. Background Scheduler (`api/services/scheduler.py`)

```python
class SchedulerService:
    # Job 1: Cache cleanup (every hour)
    async def cleanup_cache():
        # Remove expired entries from L1
        # Cull L2 if over size limit

    # Job 2: Cache statistics logging (every 15 min)
    async def log_cache_stats():
        # Log hit/miss rates, cache sizes
        # Useful for monitoring and tuning
```

**Configuration**:
- `USMS_ENABLE_SCHEDULER`: Enable/disable background jobs (default: `true`)

#### 6. Application Lifespan (`api/main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.init_db()           # Initialize SQLite for webhooks
    cache = get_cache()          # Initialize cache
    scheduler = SchedulerService()
    scheduler.start()            # Start background jobs

    yield  # Application runs

    # Shutdown
    scheduler.shutdown()         # Stop background jobs
    cache.close()               # Close disk cache
```

### API Development Workflow

#### Adding New Endpoints

1. **Define Pydantic models** in `api/models/`
   - Request models for POST/PUT bodies
   - Response models for API responses
   - Use Field() for validation and documentation

2. **Create router function** in `api/routers/`
   - Use dependency injection for auth (`CurrentAccount`)
   - Use dependency injection for cache (`CacheService`)
   - Implement caching strategy (check cache → compute → store)
   - Handle errors (let ErrorHandlerMiddleware catch them)

3. **Register router** in `api/main.py`
   ```python
   app.include_router(new_router)
   ```

4. **Update tests** (when adding API tests in future)

#### Example: Adding a New Endpoint

```python
# 1. Define model in api/models/meter.py
class MeterHistoryResponse(BaseModel):
    meter_no: str
    data: list[ConsumptionDataPoint]
    total_consumption: float

# 2. Create router function in api/routers/meters.py
@router.get("/{meter_id}/history", response_model=MeterHistoryResponse)
async def get_meter_history(
    meter_id: str,
    days: int = 30,
    account: CurrentAccount = None,
    cache: CacheService = None,
):
    # Check cache
    cache_key = f"meter:{meter_id}:history:{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Get data
    meter = account.get_meter(meter_id)
    data = await meter.get_last_n_days_hourly_consumptions(days)

    # Build response
    response = MeterHistoryResponse(
        meter_no=meter_id,
        data=data,
        total_consumption=sum(d.consumption for d in data)
    )

    # Cache it
    cache.set(cache_key, response, ttl_memory=900, ttl_disk=3600)
    return response
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `USMS_JWT_SECRET` | `CHANGE_ME_IN_PRODUCTION` | **REQUIRED** in production. Secret key for JWT signing |
| `USMS_JWT_EXPIRATION` | `86400` | Token expiration (seconds). Default: 24 hours |
| `USMS_API_HOST` | `127.0.0.1` | Server bind address |
| `USMS_API_PORT` | `8000` | Server port |
| `USMS_API_WORKERS` | `4` | Worker processes (production only, ignored with --reload) |
| `USMS_API_RELOAD` | `false` | Auto-reload on code changes (dev only) |
| `USMS_API_RATE_LIMIT` | `100` | Max requests per user per window |
| `USMS_API_RATE_WINDOW` | `3600` | Rate limit window (seconds) |
| `USMS_CACHE_MEMORY_SIZE` | `1000` | L1 cache max items |
| `USMS_ENABLE_SCHEDULER` | `true` | Enable background jobs |
| `USMS_WEBHOOK_TIMEOUT` | `10` | Webhook request timeout (seconds) |
| `USMS_WEBHOOK_MAX_FAILURES` | `3` | Max failures before disabling webhook |

### Production Deployment Considerations

1. **JWT Secret**: Generate strong secret key
   ```sh
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **HTTPS/TLS**: Use reverse proxy (nginx, Traefik, Caddy)
   ```nginx
   server {
       listen 443 ssl;
       server_name api.example.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

3. **CORS**: Update allowed origins in `api/main.py`
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Restrict origins
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["*"],
   )
   ```

4. **Monitoring**:
   - Health check: `GET /health`
   - Cache stats in logs every 15 min
   - Set up log aggregation (ELK, Grafana Loki)

5. **Database Backups**:
   - Cache: `/data/cache/` (SQLite files)
   - Webhooks: `/data/api.db` (when implemented)
   - Schedule periodic backups of `/data` volume

6. **Worker Tuning**:
   - Formula: `(2 × CPU cores) + 1`
   - Monitor with `docker stats` or `htop`
   - Adjust based on memory usage and request patterns

## Architecture

### High-Level Structure

The codebase follows a **clean, layered architecture** with clear separation of concerns:

```
src/usms/
├── core/              # Infrastructure layer (HTTP client, auth, state management)
├── models/            # Data models (dataclasses for account, meter, tariff)
├── services/          # Business logic layer
│   ├── sync/          # Synchronous implementations
│   └── async_/        # Asynchronous implementations
├── parsers/           # HTML parsing utilities
├── storage/           # Data persistence layer (abstract + SQLite/CSV implementations)
├── utils/             # Utilities (decorators, helpers, logging)
└── exceptions/        # Custom exceptions
```

### Key Architectural Patterns

1. **Dual Sync/Async Design**: Single codebase with parallel sync/async implementations
   - Base classes (`BaseUSMSAccount`, `BaseUSMSMeter`) define contracts
   - Sync and async services inherit and implement specifics
   - Client auto-detects mode using `inspect.iscoroutinefunction()`
   - Use `services/sync/` for synchronous, `services/async_/` for asynchronous

2. **Mixin Pattern**: Client functionality split into focused mixins
   - `AuthenticationMixin`: Handles login/logout
   - `StateManagerMixin`: Manages ASP.NET ViewState/EventValidation
   - Combined in `USMSClient` for full functionality

3. **Protocol-Based Typing**: Structural typing for dependency injection
   - `HTTPXClientProtocol` defines interface contract
   - Enables flexible client injection (sync/async httpx clients)
   - See `core/protocols.py`

4. **Factory Pattern**: `initialize_usms_account()` handles complex object creation
   - Manages client initialization, login, meter retrieval
   - Use factory in `factory.py` instead of direct instantiation

5. **Decorator Pattern**: `@requires_init` guards method calls
   - Ensures services are initialized before use
   - Prevents calling methods on uninitialized state
   - Applied to service methods requiring authentication

6. **Strategy Pattern**: Pluggable storage implementations
   - `BaseUSMSStorage` defines interface
   - `SQLiteStorage` and `CSVStorage` implement specifics
   - Easy to add new storage backends

### Dependency Injection Flow

Services receive dependencies via constructor (no internal instantiation):

```python
# Client is injected into services
account_service = USMSAccount(client=client, storage=storage)
meter_service = USMSMeter(client=client, storage=storage)

# Use factory for complete setup
account = await initialize_usms_account(
    username=username,
    password=password,
    meter_id=meter_id,
    sync_mode=False  # async by default
)
```

### State Management

- Services track `_initialized` flag to prevent premature method calls
- `@requires_init` decorator enforces initialization
- Refresh/update intervals prevent excessive API calls
- Last update timestamps tracked for intelligent caching

## Code Conventions

### Style
- **Line length**: 100 characters
- **Target Python**: 3.10+
- **Imports**: Absolute only (no relative imports)
- **Docstrings**: NumPy convention
- **Type hints**: Required (enforced by ruff)

### Commit Messages
- **Format**: Conventional Commits (`type(scope): description`)
- **Types**: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`
- **Versioning**: Automatic semantic versioning via commitizen
- **CHANGELOG**: Auto-updated on `cz bump`

### Testing
- **File naming**: `test_*.py`
- **Use**: pytest fixtures and parameterize for multiple cases
- **Coverage**: Reports in `reports/` directory
- **Config**: Strict markers, fail-fast (`--exitfirst`)

### Error Handling
- All custom exceptions in `exceptions/errors.py`
- Use domain-specific exceptions with descriptive messages
- Preserve stack traces when re-raising

### Logging
- Module-level loggers: `logger = logging.getLogger(__name__)`
- Structured logging with appropriate levels
- Configurable via `--log-level` CLI flag

## Important Implementation Details

### When Adding New Features

1. **Models**: Use `@dataclass` for data structures (see `models/`)
2. **Services**: Extend base classes and implement both sync/async if needed
3. **Parsers**: Isolated HTML parsing in `parsers/` for maintainability
4. **Storage**: Implement `BaseUSMSStorage` for new backends
5. **Exceptions**: Add to `exceptions/errors.py` for domain errors

### Working with the HTTP Client

- Client uses httpx with HTTP/2 support
- Authentication state managed by `AuthenticationMixin`
- ASP.NET ViewState/EventValidation handled by `StateManagerMixin`
- Use `client.get()` and `client.post()` with proper error handling

### Understanding ASP.NET State

The USMS platform uses ASP.NET Web Forms:
- `__VIEWSTATE`: Server state token (required for POST)
- `__EVENTVALIDATION`: Security token (required for POST)
- Both extracted via `parsers/asp_state_parser.py`
- Managed automatically by `StateManagerMixin`

### Tariff Calculations

- Tariff models in `models/tariff.py`
- Constants in `config/constants.py`
- Tiered pricing for electricity (different rates per kWh band)
- Water pricing based on account type
- Cost calculations include all fees and taxes

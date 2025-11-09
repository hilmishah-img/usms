# USMS

An unofficial Python library to interface with your [USMS](https://www.usms.com.bn/smartmeter/about.html) account and smart meters.

## Getting Started

### Installation

```sh
python -m pip install usms
```

### Quickstart

```sh
python -m usms --help
```

```sh
usage: __main__.py [-h] [-l LOG] -u USERNAME -p PASSWORD [-m METER] [--unit] [--consumption] [--credit]

options:
  -h, --help            show this help message and exit
  -l LOG, --log LOG
  -u USERNAME, --username USERNAME
  -p PASSWORD, --password PASSWORD
  -m METER, --meter METER
  --unit
  --consumption
  --credit
```

> [!NOTE]
> The `username` parameter is the login ID that you use to log-in on the USMS website/app, i.e. your IC Number.

As an example, you can use the following command to get the current remaining unit:

```sh
python -m usms -u <ic_number> -p <password> -m <meter> --unit
```

You can also use environment variables for the login information:

```sh
export USMS_USERNAME="<ic_number>"
export USMS_PASSWORD="<password>"
python -m usms -m <meter> --unit
```

Or:

```sh
USMS_USERNAME="<ic_number>" USMS_PASSWORD="<password>" python -m usms -m <meter> --unit
```

## Usage

```py
import httpx

from usms import initialize_usms_account

username = "01001234" # your ic number
password = "hunter1"

# initialize the account
account = initialize_usms_account(
    username=username,
    password=password,
    client=httpx.Client(),  # or httpx.AsyncClient(), optional
)

# print out the account information
print(account.name)

# print out info on all meters under the account
for meter in account.meters:
    print(meter.no)
    print(meter.type)
    print(meter.address)
    print(meter.remaining_unit)
    print(meter.remaining_credit)
    print(meter.unit)

# get the number of the second meter
meter_no = account.meters[1].no

# to get info from a specific meter
meter = account.get_meter(meter_no)

# get today's consumptions
print(meter.get_last_n_days_hourly_consumptions(n=0))

# getting daily breakdown of last month's comsumptions
daily_consumptions = meter.get_previous_n_month_consumptions(n=1)
print(daily_consumptions)
# get last month's total cost based on total consumption
print(meter.calculate_total_cost(daily_consumptions))
```

## Docker

USMS is available as a Docker container for easy deployment without Python installation.

### Pull from GitHub Container Registry

```sh
docker pull ghcr.io/azsaurr/usms:latest
```

### Usage Examples

#### List all meters

```sh
docker run --rm \
  -e USMS_USERNAME="your_ic_number" \
  -e USMS_PASSWORD="your_password" \
  ghcr.io/azsaurr/usms:latest --list
```

#### Get meter unit balance

```sh
docker run --rm \
  -e USMS_USERNAME="your_ic_number" \
  -e USMS_PASSWORD="your_password" \
  -v ./data:/data \
  ghcr.io/azsaurr/usms:latest -m METER_ID --unit
```

#### Get meter credit balance

```sh
docker run --rm \
  -e USMS_USERNAME="your_ic_number" \
  -e USMS_PASSWORD="your_password" \
  -v ./data:/data \
  ghcr.io/azsaurr/usms:latest -m METER_ID --credit
```

#### Using docker-compose

Create a `.env` file with your credentials:

```env
USMS_USERNAME=your_ic_number
USMS_PASSWORD=your_password
METER_ID=your_meter_id
```

Then use the provided `docker-compose.prod.yml`:

```sh
# List all meters
docker-compose -f docker-compose.prod.yml --profile list up

# Get meter unit balance
docker-compose -f docker-compose.prod.yml --profile unit up

# Get meter credit balance
docker-compose -f docker-compose.prod.yml --profile credit up
```

#### Data Persistence

Mount a volume to `/data` to persist SQLite databases and CSV files:

```sh
docker run --rm \
  -e USMS_USERNAME="your_ic_number" \
  -e USMS_PASSWORD="your_password" \
  -v $(pwd)/data:/data \
  ghcr.io/azsaurr/usms:latest -m METER_ID --unit
```

#### Available Tags

- `latest` - Latest stable release
- `vX.Y.Z` - Specific version (e.g., `v0.9.2`)
- `X.Y` - Major.minor version (e.g., `0.9`)
- `X` - Major version (e.g., `0`)

### Building Locally

To build the production image locally:

```sh
docker build --target runtime -t usms:local .
```

To build for multiple platforms:

```sh
docker buildx build --platform linux/amd64,linux/arm64 --target runtime -t usms:local .
```

## REST API

USMS includes a production-ready REST API that exposes all library functionality via HTTP endpoints. The API features JWT authentication, rate limiting, hybrid caching, and background job scheduling.

### Installation

Install with API dependencies:

```sh
pip install usms[api]
```

### Quick Start

Start the API server:

```sh
# Using the CLI
python -m usms serve

# With custom host and port
python -m usms serve --host 0.0.0.0 --port 8000

# Development mode with auto-reload
python -m usms serve --reload
```

The API will be available at `http://127.0.0.1:8000` with interactive documentation at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI spec: `http://127.0.0.1:8000/openapi.json`

### Features

- **JWT Authentication**: Secure token-based authentication with encrypted credentials
- **Rate Limiting**: Configurable rate limits per user (default: 100 requests/hour)
- **Hybrid Caching**: Two-tier cache (in-memory + SQLite) for optimal performance
- **Background Jobs**: Automatic cache cleanup and maintenance
- **Error Handling**: Consistent error responses across all endpoints
- **CORS Support**: Configurable cross-origin resource sharing
- **Health Checks**: Built-in health check endpoint for monitoring
- **Auto-generated Docs**: Interactive API documentation with try-it-out functionality

### API Endpoints

#### Authentication
- `POST /auth/login` - Login and get JWT token
- `GET /auth/verify` - Verify token validity
- `POST /auth/refresh` - Refresh account data
- `POST /auth/logout` - Logout (invalidate token)

#### Account
- `GET /account` - Get account information
- `POST /account/refresh` - Force refresh account data

#### Meters
- `GET /meters/{meter_id}` - Get meter information
- `GET /meters/{meter_id}/unit` - Get meter unit balance
- `GET /meters/{meter_id}/credit` - Get meter credit balance
- `GET /meters/{meter_id}/consumption/hourly` - Get hourly consumption
- `GET /meters/{meter_id}/consumption/daily` - Get daily consumption
- `POST /meters/{meter_id}/cost/calculate` - Calculate cost for consumption

#### Tariffs
- `GET /tariffs/electricity` - Get electricity tariff information
- `GET /tariffs/water` - Get water tariff information

### Docker Usage (API Server)

#### Using docker-compose (Recommended)

Create a `.env` file:

```env
# JWT Configuration (REQUIRED - change in production!)
JWT_SECRET=your_very_secure_secret_key_change_me

# API Configuration
API_PORT=8000
API_WORKERS=4

# Rate Limiting
RATE_LIMIT=100
RATE_WINDOW=3600

# Cache Configuration
CACHE_MEMORY_SIZE=1000

# Background Jobs
ENABLE_SCHEDULER=true
```

Start the API server:

```sh
# Production mode (4 workers)
docker-compose -f docker-compose.prod.yml --profile api up -d

# Development mode (with auto-reload)
docker-compose -f docker-compose.prod.yml --profile api-dev up
```

#### Using docker run

```sh
docker run -d \
  --name usms-api \
  -p 8000:8000 \
  -e USMS_JWT_SECRET="your_secret_key" \
  -v usms-data:/data \
  ghcr.io/azsaurr/usms:latest \
  serve --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USMS_JWT_SECRET` | `CHANGE_ME_IN_PRODUCTION` | Secret key for JWT token signing (REQUIRED in production) |
| `USMS_JWT_EXPIRATION` | `86400` | JWT token expiration time in seconds (24 hours) |
| `USMS_API_HOST` | `127.0.0.1` | API server host |
| `USMS_API_PORT` | `8000` | API server port |
| `USMS_API_WORKERS` | `4` | Number of worker processes (production) |
| `USMS_API_RATE_LIMIT` | `100` | Maximum requests per user per window |
| `USMS_API_RATE_WINDOW` | `3600` | Rate limit window in seconds (1 hour) |
| `USMS_CACHE_MEMORY_SIZE` | `1000` | Maximum number of items in memory cache |
| `USMS_ENABLE_SCHEDULER` | `true` | Enable background job scheduler |

### Example API Usage

#### Login and get token

```sh
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "01001234", "password": "your_password"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### Get account information

```sh
curl -X GET "http://localhost:8000/account" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Get meter unit balance

```sh
curl -X GET "http://localhost:8000/meters/METER_ID/unit" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Get hourly consumption

```sh
curl -X GET "http://localhost:8000/meters/METER_ID/consumption/hourly?days=7" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Production Deployment Checklist

- [ ] Change `USMS_JWT_SECRET` to a strong, unique secret key
- [ ] Configure `USMS_API_RATE_LIMIT` based on your needs
- [ ] Set up HTTPS/TLS (use reverse proxy like nginx or Traefik)
- [ ] Configure CORS allowed origins (update `api/main.py`)
- [ ] Set up monitoring and logging
- [ ] Configure backup for `/data` volume (contains SQLite cache)
- [ ] Review and adjust worker count based on server resources

> **📖 For comprehensive production deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)**
>
> The deployment guide includes:
> - Step-by-step setup instructions
> - Environment configuration details
> - Reverse proxy setup (nginx, Traefik, Caddy)
> - Monitoring and maintenance procedures
> - Backup and recovery strategies
> - Troubleshooting guide
> - Security best practices

## To-Do

* [ ] Add more test coverage
* [x] Support for water meter
* [ ] Support for commercial/corporate accounts

## Contributing

### Prerequisites

1. [Generate an SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key) and [add the SSH key to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).
1. Configure SSH to automatically load your SSH keys:

    ```sh
    cat << EOF >> ~/.ssh/config
    
    Host *
      AddKeysToAgent yes
      IgnoreUnknown UseKeychain
      UseKeychain yes
      ForwardAgent yes
    EOF
    ```

1. [Install Docker Desktop](https://www.docker.com/get-started).
1. [Install VS Code](https://code.visualstudio.com/) and [VS Code's Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers). Alternatively, install [PyCharm](https://www.jetbrains.com/pycharm/download/).
1. _Optional:_ install a [Nerd Font](https://www.nerdfonts.com/font-downloads) such as [FiraCode Nerd Font](https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts/FiraCode) and [configure VS Code](https://github.com/tonsky/FiraCode/wiki/VS-Code-Instructions) or [PyCharm](https://github.com/tonsky/FiraCode/wiki/Intellij-products-instructions) to use it.

### Development Environments

The following development environments are supported:

1. ⭐️ _GitHub Codespaces_: click on [Open in GitHub Codespaces](https://github.com/codespaces/new/user/user) to start developing in your browser.
1. ⭐️ _VS Code Dev Container (with container volume)_: click on [Open in Dev Containers](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/user/user) to clone this repository in a container volume and create a Dev Container with VS Code.
1. ⭐️ _uv_: clone this repository and run the following from root of the repository:

    ```sh
    # Create and install a virtual environment
    uv sync --python 3.10 --all-extras

    # Activate the virtual environment
    source .venv/bin/activate

    # Install the pre-commit hooks
    pre-commit install --install-hooks
    ```

1. _VS Code Dev Container_: clone this repository, open it with VS Code, and run <kbd>Ctrl/⌘</kbd> + <kbd>⇧</kbd> + <kbd>P</kbd> → _Dev Containers: Reopen in Container_.
1. _PyCharm Dev Container_: clone this repository, open it with PyCharm, [create a Dev Container with Mount Sources](https://www.jetbrains.com/help/pycharm/start-dev-container-inside-ide.html), and [configure an existing Python interpreter](https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html#widget) at `/opt/venv/bin/python`.
2. _nix develop_: clone this repository and run `nix develop`.

### Developing

* This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
* Run `poe` from within the development environment to print a list of [Poe the Poet](https://github.com/nat-n/poethepoet) tasks available to run on this project.
* Run `uv add {package}` from within the development environment to install a run time dependency and add it to `pyproject.toml` and `uv.lock`. Add `--dev` to install a development dependency.
* Run `uv sync --upgrade` from within the development environment to upgrade all dependencies to the latest versions allowed by `pyproject.toml`. Add `--only-dev` to upgrade the development dependencies only.
* Run `cz bump` to bump the package's version, update the `CHANGELOG.md`, and create a git tag. Then push the changes and the git tag with `git push origin main --tags`.

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgments

* [USMS](https://www.usms.com.bn/smartmeter/about.html)

### Project Template

This project was built using the [superlinear-ai/substrate](https://github.com/superlinear-ai/substrate) template.

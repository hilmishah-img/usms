"""USMS REST API module.

This module provides a FastAPI-based REST API for accessing USMS functionality.

To start the API server:
    python -m usms serve --host 0.0.0.0 --port 8000

For development with auto-reload:
    python -m usms serve --reload

Installation:
    pip install usms[api]
    # or
    uv sync --extra api
"""

__all__ = ["app", "create_app"]

from usms.api.main import app, create_app

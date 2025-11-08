"""Server module for running the API."""

import sys


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    workers: int = 1,
) -> None:
    """Run the USMS API server.

    Parameters
    ----------
    host : str, optional
        Host to bind to, by default "127.0.0.1"
    port : int, optional
        Port to bind to, by default 8000
    reload : bool, optional
        Enable auto-reload for development, by default False
    workers : int, optional
        Number of worker processes, by default 1

    Raises
    ------
    SystemExit
        If API dependencies are not installed

    Notes
    -----
    This function starts a uvicorn server with the FastAPI application.
    It requires the API optional dependencies to be installed:
        pip install usms[api]
    """
    try:
        import uvicorn
    except ImportError:
        print(
            "Error: API dependencies not installed.\n"
            "Please install with: pip install usms[api]\n"
            "or: uv sync --extra api",
            file=sys.stderr,
        )
        sys.exit(1)

    # Override workers if reload is enabled
    if reload:
        workers = 1
        print("⚠️  Auto-reload enabled, running with 1 worker")

    print(f"🚀 Starting USMS API server on http://{host}:{port}")
    print(f"📚 API documentation: http://{host}:{port}/docs")
    print(f"🔍 OpenAPI spec: http://{host}:{port}/openapi.json")

    uvicorn.run(
        "usms.api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level="info",
    )

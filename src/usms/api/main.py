"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from usms.api.config import get_settings
from usms.api.database import get_database
from usms.api.middleware.error_handler import ErrorHandlerMiddleware
from usms.api.middleware.rate_limit import RateLimitMiddleware
from usms.api.routers import account_router, auth_router, meters_router, tariffs_router
from usms.api.services.cache import get_cache
from usms.api.services.scheduler import SchedulerService

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: SchedulerService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events.

    Parameters
    ----------
    app : FastAPI
        FastAPI application instance

    Yields
    ------
    None
        Control during application lifetime
    """
    global _scheduler

    # Startup
    logger.info("🚀 USMS API starting up...")

    # Initialize database
    db = get_database()
    await db.init_db()
    logger.info("✅ Database initialized")

    # Initialize cache
    cache = get_cache()
    logger.info("✅ Cache initialized")

    # Start scheduler for background jobs
    settings = get_settings()
    if settings.ENABLE_SCHEDULER:
        _scheduler = SchedulerService()
        _scheduler.start()
        logger.info("✅ Scheduler started")

    logger.info("🎉 USMS API startup complete!")

    yield

    # Shutdown
    logger.info("👋 USMS API shutting down...")

    # Shutdown scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("✅ Scheduler stopped")

    # Close cache
    cache.close()
    logger.info("✅ Cache closed")

    logger.info("✅ USMS API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns
    -------
    FastAPI
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        contact=settings.API_CONTACT,
        license_info=settings.API_LICENSE,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add middleware (order matters! Last added = first executed)
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        limit=settings.RATE_LIMIT,
        window=settings.RATE_WINDOW,
    )

    # Error handler middleware (should be last to catch all errors)
    app.add_middleware(ErrorHandlerMiddleware)

    # Include routers
    app.include_router(auth_router)
    app.include_router(account_router)
    app.include_router(meters_router)
    app.include_router(tariffs_router)

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> JSONResponse:
        """Root endpoint with API information."""
        return JSONResponse(
            content={
                "message": "USMS REST API",
                "version": settings.API_VERSION,
                "docs": "/docs",
                "openapi": "/openapi.json",
            }
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health() -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse(content={"status": "healthy"})

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "usms.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        workers=settings.API_WORKERS if not settings.API_RELOAD else 1,
    )

"""API route handlers."""

__all__ = ["auth_router", "account_router", "meters_router", "tariffs_router"]

from usms.api.routers.auth import router as auth_router
from usms.api.routers.account import router as account_router
from usms.api.routers.meters import router as meters_router
from usms.api.routers.tariffs import router as tariffs_router

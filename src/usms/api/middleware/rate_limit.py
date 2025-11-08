"""Rate limiting middleware using in-memory TTL cache."""

import json
import logging
from datetime import datetime

from cachetools import TTLCache
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from usms.api.dependencies import verify_token

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window algorithm.

    Attributes
    ----------
    limit : int
        Maximum requests per window
    window : int
        Time window in seconds
    requests : TTLCache
        In-memory cache of request timestamps per user
    """

    def __init__(self, app, limit: int = 100, window: int = 3600):
        """Initialize rate limiter.

        Parameters
        ----------
        app : FastAPI
            FastAPI application instance
        limit : int, optional
            Maximum requests per window, by default 100
        window : int, optional
            Time window in seconds, by default 3600 (1 hour)
        """
        super().__init__(app)
        self.limit = limit
        self.window = window
        # TTLCache automatically removes expired entries
        self.requests = TTLCache(maxsize=10000, ttl=window)

        logger.info(f"Rate limiter initialized: {limit} req/{window}s")

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting.

        Parameters
        ----------
        request : Request
            Incoming HTTP request
        call_next : callable
            Next middleware in chain

        Returns
        -------
        Response
            HTTP response with rate limit headers
        """
        # Skip rate limiting for certain paths
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Skip rate limiting for auth endpoints (need to login first!)
        if request.url.path.startswith("/auth"):
            return await call_next(request)

        # Extract user_id from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # No auth = no rate limiting (will fail at endpoint anyway)
            return await call_next(request)

        try:
            # Extract user_id from JWT
            token = auth_header.split(" ")[1]
            token_data = verify_token(token)
            user_id = token_data.user_id
        except Exception as e:
            logger.debug(f"Rate limit: Invalid token, skipping: {e}")
            # Invalid token will be caught by endpoint auth
            return await call_next(request)

        # Track requests for this user
        now = datetime.now().timestamp()

        if user_id not in self.requests:
            self.requests[user_id] = []

        # Remove old requests (outside window) - TTLCache does this automatically
        # but we need precise control for per-user limits
        self.requests[user_id] = [
            ts for ts in self.requests[user_id] if now - ts < self.window
        ]

        # Check limit
        current_count = len(self.requests[user_id])

        if current_count >= self.limit:
            # Rate limit exceeded
            oldest_request = min(self.requests[user_id])
            retry_after = int(self.window - (now - oldest_request))

            return Response(
                content=json.dumps(
                    {
                        "detail": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                        "retry_after": retry_after,
                    }
                ),
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                    "Retry-After": str(retry_after),
                },
            )

        # Add current request
        self.requests[user_id].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        remaining = self.limit - len(self.requests[user_id])
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.window))

        return response

"""Error handling middleware for consistent error responses."""

import logging
from datetime import datetime

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from usms.exceptions.errors import (
    USMSConsumptionHistoryNotFoundError,
    USMSFutureDateError,
    USMSInvalidParameterError,
    USMSLoginError,
    USMSMeterNumberError,
    USMSMissingCredentialsError,
    USMSNotInitializedError,
    USMSPageResponseError,
)

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling USMS exceptions and returning consistent errors.

    Catches all exceptions and returns JSON error responses with
    appropriate HTTP status codes.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request with error handling.

        Parameters
        ----------
        request : Request
            Incoming HTTP request
        call_next : callable
            Next middleware in chain

        Returns
        -------
        Response
            HTTP response, potentially error response
        """
        try:
            response = await call_next(request)
            return response

        except USMSMeterNumberError as e:
            logger.warning(f"Meter not found: {e}")
            return JSONResponse(
                status_code=404,
                content={
                    "detail": str(e),
                    "error_code": "METER_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except USMSLoginError as e:
            logger.warning(f"Authentication failed: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "detail": str(e),
                    "error_code": "AUTHENTICATION_FAILED",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except USMSMissingCredentialsError as e:
            logger.warning(f"Missing credentials: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "detail": str(e),
                    "error_code": "MISSING_CREDENTIALS",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except USMSNotInitializedError as e:
            logger.error(f"Service not initialized: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": str(e),
                    "error_code": "SERVICE_NOT_INITIALIZED",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except USMSFutureDateError as e:
            logger.warning(f"Future date provided: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "detail": str(e),
                    "error_code": "INVALID_DATE",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except USMSConsumptionHistoryNotFoundError as e:
            logger.info(f"Consumption history not found: {e}")
            return JSONResponse(
                status_code=404,
                content={
                    "detail": str(e),
                    "error_code": "DATA_NOT_FOUND",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except USMSInvalidParameterError as e:
            logger.warning(f"Invalid parameter: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "detail": str(e),
                    "error_code": "INVALID_PARAMETER",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except USMSPageResponseError as e:
            logger.error(f"USMS platform error: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "USMS platform is unavailable or returned unexpected response",
                    "error_code": "USMS_UNAVAILABLE",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except ValueError as e:
            logger.warning(f"Value error: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "detail": str(e),
                    "error_code": "VALIDATION_ERROR",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            # Log with full traceback for debugging
            logger.error(f"Unhandled error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error_code": "INTERNAL_ERROR",
                    "timestamp": datetime.now().isoformat(),
                },
            )

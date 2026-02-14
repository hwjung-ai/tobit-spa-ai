"""FastAPI global exception handlers"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .exceptions import AppBaseError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppBaseError) -> JSONResponse:
    """Handle AppBaseError exceptions with proper logging and response"""
    request_id = request.headers.get("X-Request-ID", "N/A")
    extra_context = {
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
    }

    # Log based on severity
    if exc.status_code >= 500:
        logger.error(
            f"Server error {exc.code}: {exc.message}",
            extra=extra_context,
            exc_info=True,
        )
    elif exc.code == "TENANT_VIOLATION":
        # Security violation - log as warning with audit implications
        logger.warning(
            f"Security: Tenant isolation violation - {exc.message}",
            extra=extra_context,
        )
    elif exc.status_code == 429:  # Rate limit
        logger.warning(
            f"Rate limit {exc.code}: {exc.message}",
            extra=extra_context,
        )
    elif exc.status_code == 403:  # Authorization
        logger.warning(
            f"Authorization error {exc.code}: {exc.message}",
            extra=extra_context,
        )
    elif exc.status_code == 404:  # Not found
        logger.info(
            f"Not found {exc.code}: {exc.message}",
            extra=extra_context,
        )
    else:
        logger.warning(
            f"Client error {exc.code}: {exc.message}",
            extra=extra_context,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "status_code": exc.status_code,
            "request_id": request_id,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    request_id = request.headers.get("X-Request-ID", "N/A")
    extra_context = {
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
    }

    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra=extra_context,
        exc_info=True,
    )

    # Don't expose internal details in production
    message = "Internal server error"
    if hasattr(exc, "detail"):
        message = exc.detail

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": message,
            "status_code": 500,
            "request_id": request_id,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with FastAPI app"""
    app.add_exception_handler(AppBaseError, app_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

"""
OPS Module Error Handler

Provides centralized exception handling for the OPS module, including
custom exception handlers for FastAPI integration.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from schemas import ResponseEnvelope

from .errors import (
    ExecutionException,
    OPSException,
    PlanningException,
    StageExecutionException,
    ToolNotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)


def ops_exception_handler(request: Request, exc: OPSException) -> JSONResponse:
    """Handle OPS exceptions and return structured error response.

    Args:
        request: The HTTP request
        exc: The OPS exception

    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"OPS exception: {exc.message}",
        extra={
            "code": exc.code,
            "details": exc.details,
            "path": request.url.path,
        },
    )

    response = ResponseEnvelope.error(
        code=exc.code,
        message=exc.message,
    )

    if exc.details:
        response.data = exc.details

    return JSONResponse(
        status_code=exc.code,
        content=response.model_dump(),
    )


def planning_exception_handler(request: Request, exc: PlanningException) -> JSONResponse:
    """Handle planning exceptions.

    Args:
        request: The HTTP request
        exc: The planning exception

    Returns:
        JSONResponse with error details
    """
    return ops_exception_handler(request, exc)


def execution_exception_handler(
    request: Request, exc: ExecutionException
) -> JSONResponse:
    """Handle execution exceptions.

    Args:
        request: The HTTP request
        exc: The execution exception

    Returns:
        JSONResponse with error details
    """
    return ops_exception_handler(request, exc)


def validation_exception_handler(
    request: Request, exc: ValidationException
) -> JSONResponse:
    """Handle validation exceptions.

    Args:
        request: The HTTP request
        exc: The validation exception

    Returns:
        JSONResponse with error details
    """
    return ops_exception_handler(request, exc)


def tool_not_found_handler(request: Request, exc: ToolNotFoundException) -> JSONResponse:
    """Handle tool not found exceptions.

    Args:
        request: The HTTP request
        exc: The tool not found exception

    Returns:
        JSONResponse with error details
    """
    return ops_exception_handler(request, exc)


def stage_execution_exception_handler(
    request: Request, exc: StageExecutionException
) -> JSONResponse:
    """Handle stage execution exceptions.

    Args:
        request: The HTTP request
        exc: The stage execution exception

    Returns:
        JSONResponse with error details
    """
    return ops_exception_handler(request, exc)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all OPS exception handlers with FastAPI app.

    This function should be called during app initialization to enable
    proper exception handling for all OPS module exceptions.

    Args:
        app: The FastAPI application instance
    """
    app.add_exception_handler(OPSException, ops_exception_handler)
    app.add_exception_handler(PlanningException, planning_exception_handler)
    app.add_exception_handler(ExecutionException, execution_exception_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(ToolNotFoundException, tool_not_found_handler)
    app.add_exception_handler(
        StageExecutionException, stage_execution_exception_handler
    )

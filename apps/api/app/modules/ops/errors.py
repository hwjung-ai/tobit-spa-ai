"""
OPS Module Exception Classes

Provides custom exceptions for the OPS module to enable consistent error handling
and better error categorization across different operations.

Exception Hierarchy:
    OPSException (base)
    ├── PlanningException
    ├── ExecutionException
    ├── ValidationException
    ├── ToolNotFoundException
    └── StageExecutionException
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class OPSException(Exception):
    """Base exception class for all OPS module errors.

    Attributes:
        code: HTTP status code or error code
        message: Human-readable error message
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize OPSException.

        Args:
            message: Human-readable error message
            code: HTTP status code or error code (default: 500)
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response.

        Returns:
            Dictionary with code, message, and details
        """
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class PlanningException(OPSException):
    """Exception raised during planning phase.

    Occurs when there are issues with:
    - Plan generation
    - Plan validation
    - Intent processing
    """

    def __init__(
        self,
        message: str,
        code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize PlanningException."""
        super().__init__(message, code, details)


class ExecutionException(OPSException):
    """Exception raised during execution phase.

    Occurs when there are issues with:
    - Stage execution
    - Tool execution
    - Result processing
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize ExecutionException."""
        super().__init__(message, code, details)


class ValidationException(OPSException):
    """Exception raised when validation fails.

    Occurs when:
    - Request payload validation fails
    - Input data validation fails
    - Configuration validation fails
    """

    def __init__(
        self,
        message: str,
        code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize ValidationException."""
        super().__init__(message, code, details)


class ToolNotFoundException(OPSException):
    """Exception raised when a required tool is not found.

    Occurs when:
    - Tool is not registered in action registry
    - Tool implementation is missing
    - Tool configuration is incomplete
    """

    def __init__(
        self,
        message: str,
        code: int = 404,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize ToolNotFoundException."""
        super().__init__(message, code, details)


class StageExecutionException(OPSException):
    """Exception raised during stage execution.

    Occurs when:
    - Stage setup fails
    - Stage execution fails
    - Stage results processing fails
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize StageExecutionException."""
        super().__init__(message, code, details)

"""Application exception classes - centralized error hierarchy"""


class AppBaseError(Exception):
    """Base application error with code and message"""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response"""
        return {
            "error": self.code,
            "message": self.message,
            "status_code": self.status_code,
        }


class ConnectionError(AppBaseError):
    """DB/Redis/external service connection failure (retryable)"""

    def __init__(self, service: str, message: str):
        super().__init__(
            f"{service} connection failed: {message}",
            "CONNECTION_ERROR",
            503,
        )
        self.service = service


class TimeoutError(AppBaseError):
    """Operation timeout (escalation needed)"""

    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(
            f"{operation} timed out after {timeout_seconds}s",
            "TIMEOUT",
            504,
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class ValidationError(AppBaseError):
    """Input validation failure (400 response)"""

    def __init__(self, field: str, message: str):
        super().__init__(
            f"Validation failed for {field}: {message}",
            "VALIDATION_ERROR",
            400,
        )
        self.field = field


class TenantIsolationError(AppBaseError):
    """Tenant isolation violation (403 response, audit log required)"""

    def __init__(self, tenant_id: str, message: str = ""):
        msg = f"Tenant isolation violation: {tenant_id}"
        if message:
            msg += f" - {message}"
        super().__init__(msg, "TENANT_VIOLATION", 403)
        self.tenant_id = tenant_id


class ToolExecutionError(AppBaseError):
    """Tool execution failure"""

    def __init__(self, tool_name: str, message: str):
        super().__init__(
            f"Tool '{tool_name}' failed: {message}",
            "TOOL_ERROR",
            500,
        )
        self.tool_name = tool_name


class PlanningError(AppBaseError):
    """LLM plan generation failure"""

    def __init__(self, message: str):
        super().__init__(message, "PLANNING_ERROR", 500)


class CircuitOpenError(AppBaseError):
    """Circuit breaker is open (service degraded)"""

    def __init__(self, service: str):
        super().__init__(
            f"Circuit breaker open for {service} - service temporarily unavailable",
            "CIRCUIT_OPEN",
            503,
        )
        self.service = service


class DatabaseError(AppBaseError):
    """Database operation failure"""

    def __init__(self, message: str):
        super().__init__(f"Database error: {message}", "DATABASE_ERROR", 503)


class ExternalServiceError(AppBaseError):
    """External service call failure"""

    def __init__(self, service: str, message: str):
        super().__init__(
            f"External service '{service}' error: {message}",
            "EXTERNAL_SERVICE_ERROR",
            503,
        )
        self.service = service


class RateLimitError(AppBaseError):
    """Rate limit exceeded"""

    def __init__(self, service: str, retry_after: float):
        super().__init__(
            f"Rate limit exceeded for {service}. Retry after {retry_after}s",
            "RATE_LIMIT_EXCEEDED",
            429,
        )
        self.service = service
        self.retry_after = retry_after


class ConfigurationError(AppBaseError):
    """Configuration or initialization error"""

    def __init__(self, message: str):
        super().__init__(message, "CONFIGURATION_ERROR", 500)


class NotFoundError(AppBaseError):
    """Resource not found"""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} with id '{resource_id}' not found",
            "NOT_FOUND",
            404,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class AuthorizationError(AppBaseError):
    """User lacks required permissions"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)


class ConflictError(AppBaseError):
    """Resource conflict (e.g., duplicate, state mismatch)"""

    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)

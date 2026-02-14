"""API Manager Copilot API Schemas."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ApiCopilotContext(BaseModel):
    """Additional context for API copilot."""
    available_databases: list[str] = Field(
        default_factory=list,
        description="List of available databases for SQL APIs"
    )
    available_workflows: list[str] = Field(
        default_factory=list,
        description="List of available workflows"
    )
    common_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Common HTTP headers (e.g., Authorization, Content-Type)"
    )


class ApiCopilotRequest(BaseModel):
    """Request schema for API copilot."""
    prompt: str = Field(
        ...,
        description="User's natural language request for API generation/modification",
        min_length=1,
        max_length=2000
    )
    api_draft: Optional[dict[str, Any]] = Field(
        default=None,
        description="Existing API draft to modify/enhance"
    )
    logic_type: Optional[Literal["sql", "http", "python", "workflow"]] = Field(
        default=None,
        description="Type of API logic (if provided)"
    )
    context: Optional[ApiCopilotContext] = Field(
        default=None,
        description="Additional context for better suggestions"
    )


class HttpSpecGeneration(BaseModel):
    """Generated HTTP specification."""
    url: str = Field(..., description="API endpoint URL")
    method: Literal["GET", "POST", "PUT", "DELETE"] = Field(
        default="GET",
        description="HTTP method"
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers"
    )
    body: Optional[dict[str, Any]] = Field(
        default=None,
        description="Request body template (for POST/PUT)"
    )
    params: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameters"
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Example requests/responses"
    )


class ApiCopilotResponse(BaseModel):
    """Response schema for API copilot."""
    api_draft: dict[str, Any] = Field(
        ...,
        description="Generated or modified API draft"
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of the generated API"
    )
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Additional suggestions for improvement"
    )
    http_spec: Optional[HttpSpecGeneration] = Field(
        default=None,
        description="Generated HTTP specification (for HTTP APIs)"
    )
    request_example: Optional[dict[str, Any]] = Field(
        default=None,
        description="Example request payload"
    )
    response_example: Optional[dict[str, Any]] = Field(
        default=None,
        description="Example response payload"
    )


class ApiCopilotError(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error info")

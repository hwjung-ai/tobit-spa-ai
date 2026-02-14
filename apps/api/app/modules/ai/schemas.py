"""Screen Copilot API Schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ScreenCopilotContext(BaseModel):
    """Additional context for screen copilot."""
    available_handlers: list[str] = Field(
        default_factory=list,
        description="List of available action handlers"
    )
    state_paths: list[str] = Field(
        default_factory=list,
        description="Available state binding paths"
    )


class ScreenCopilotRequest(BaseModel):
    """Request schema for screen copilot API."""
    screen_schema: dict[str, Any] = Field(
        ...,
        description="Current screen schema (ScreenSchemaV1)"
    )
    prompt: str = Field(
        ...,
        description="User's natural language request",
        min_length=1,
        max_length=2000
    )
    selected_component: Optional[str] = Field(
        default=None,
        description="Currently selected component ID"
    )
    context: Optional[ScreenCopilotContext] = Field(
        default=None,
        description="Additional context for better suggestions"
    )


class JsonPatchOperation(BaseModel):
    """Single JSON Patch operation (RFC6902)."""
    op: str = Field(..., description="Operation: add, remove, replace, move, copy, test")
    path: str = Field(..., description="JSON Pointer path")
    value: Optional[Any] = Field(default=None, description="Value for add/replace/test")
    from_path: Optional[str] = Field(default=None, alias="from", description="Source path for move/copy")

    class Config:
        populate_by_name = True


class ScreenCopilotResponse(BaseModel):
    """Response schema for screen copilot API."""
    patch: list[JsonPatchOperation] = Field(
        default_factory=list,
        description="JSON Patch operations to apply"
    )
    explanation: str = Field(
        default="",
        description="Human-readable explanation of changes"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Additional suggestions for the user"
    )


class ScreenCopilotError(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error info")

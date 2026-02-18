"""CEP Copilot Request/Response schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class CepCopilotContext(BaseModel):
    """Additional context for CEP copilot."""

    available_trigger_types: Optional[list[str]] = Field(
        default=None, description="List of available trigger types"
    )
    available_actions: Optional[list[str]] = Field(
        default=None, description="List of available action types"
    )


class CepCopilotRequest(BaseModel):
    """Request schema for CEP copilot API."""

    rule_spec: dict[str, Any] = Field(
        ..., description="Current CEP rule specification"
    )
    prompt: str = Field(
        ..., description="User's natural language request", min_length=1, max_length=2000
    )
    selected_field: Optional[str] = Field(
        default=None, description="Currently selected field in the editor"
    )
    context: Optional[CepCopilotContext] = Field(
        default=None, description="Additional context for better suggestions"
    )
    mode: Optional[str] = Field(
        default="create", description="Operation mode: create, modify, or patch"
    )


class CepCopilotResponse(BaseModel):
    """Response schema for CEP copilot API."""

    rule_draft: dict[str, Any] = Field(
        default_factory=dict, description="Generated or modified CEP rule draft"
    )
    patch: list[dict[str, Any]] = Field(
        default_factory=list, description="JSON Patch operations (for patch mode)"
    )
    explanation: str = Field(
        default="", description="Explanation of what was generated/modified"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="List of improvement suggestions"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of warnings or considerations"
    )

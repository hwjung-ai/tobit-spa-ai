"""SIM Copilot Request/Response schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SimCopilotContext(BaseModel):
    """Additional context for SIM copilot."""

    available_services: Optional[list[str]] = Field(
        default=None,
        description="List of available services for simulation"
    )
    available_strategies: Optional[list[str]] = Field(
        default=None,
        description="List of available strategies"
    )


class SimCopilotRequest(BaseModel):
    """Request schema for SIM copilot API."""

    current_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Current simulation parameters"
    )
    prompt: str = Field(
        ...,
        description="User's natural language request",
        min_length=1,
        max_length=2000
    )
    latest_results: Optional[dict[str, Any]] = Field(
        default=None,
        description="Latest simulation results for analysis"
    )
    context: Optional[SimCopilotContext] = Field(
        default=None,
        description="Additional context"
    )
    mode: Optional[str] = Field(
        default="draft",
        description="Operation mode: draft or analyze"
    )


class SimDraftResponse(BaseModel):
    """Response for draft mode."""

    question: str = Field(default="", description="Simulation question")
    scenario_type: str = Field(default="what_if", description="Scenario type")
    strategy: str = Field(default="rule", description="Strategy")
    horizon: str = Field(default="7d", description="Prediction horizon")
    service: str = Field(default="", description="Target service")
    assumptions: dict[str, float] = Field(
        default_factory=dict,
        description="Assumptions"
    )


class SimAnalysisResponse(BaseModel):
    """Response for analysis mode."""

    summary: str = Field(default="", description="Brief summary")
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key findings"
    )
    anomalies: list[str] = Field(
        default_factory=list,
        description="Detected anomalies"
    )
    comparison_with_baseline: str = Field(
        default="",
        description="Baseline comparison"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations"
    )
    confidence_assessment: str = Field(
        default="medium",
        description="Confidence level"
    )


class SimCopilotResponse(BaseModel):
    """Response schema for SIM copilot API."""

    mode: str = Field(default="draft", description="Response mode")
    draft: Optional[SimDraftResponse] = Field(
        default=None,
        description="Draft response"
    )
    analysis: Optional[SimAnalysisResponse] = Field(
        default=None,
        description="Analysis response"
    )
    explanation: str = Field(default="", description="Explanation")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    suggestions: list[str] = Field(default_factory=list)

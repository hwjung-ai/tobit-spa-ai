"""Regression analysis schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RegressionType(str, Enum):
    """Types of regression analysis."""

    STAGE = "stage"
    ASSET_VERSION = "asset_version"
    TIME_SERIES = "time_series"


class StageComparisonInput(BaseModel):
    """Input for stage comparison analysis."""

    baseline_trace_id: str = Field(..., description="Baseline trace ID")
    comparison_trace_id: str = Field(..., description="Comparison trace ID")
    stages: List[str] = Field(
        default=["route_plan", "validate", "execute", "compose", "present"],
        description="Stages to compare",
    )


class StageMetrics(BaseModel):
    """Metrics for a single stage."""

    stage_name: str
    duration_ms: int
    status: str
    input_size: int = Field(default=0, description="Size of input data in bytes")
    output_size: int = Field(default=0, description="Size of output data in bytes")
    reference_count: int = Field(default=0, description="Number of references")
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")


class StageRegressionReport(BaseModel):
    """Regression report for stage comparison."""

    stage_name: str
    baseline_metrics: StageMetrics
    current_metrics: StageMetrics
    differences: Dict[str, Any] = Field(default_factory=dict)
    regression_score: int = Field(ge=0, le=100, description="Regression score 0-100")
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class RegressionAnalysisRequest(BaseModel):
    """Request for regression analysis."""

    type: RegressionType
    baseline_trace_id: str
    comparison_trace_id: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class RegressionAnalysisResult(BaseModel):
    """Result of regression analysis."""

    analysis_id: str
    type: RegressionType
    baseline_trace_id: str
    comparison_trace_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "pending"

    # Stage-level results
    stage_reports: List[StageRegressionReport] = Field(default_factory=list)

    # Overall metrics
    overall_regression_score: int = Field(ge=0, le=100)
    significant_changes: int = Field(default=0)
    critical_issues: List[str] = Field(default_factory=list)

    # Summary
    summary: str = ""
    recommendations: List[str] = Field(default_factory=list)


class StageCompareResponse(BaseModel):
    """Response for stage comparison API."""

    baseline_trace: Dict[str, Any]
    comparison_trace: Dict[str, Any]
    stage_differences: Dict[str, Dict[str, Any]]
    regression_scores: Dict[str, int]
    overall_assessment: str

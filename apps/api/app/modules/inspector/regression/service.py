"""Regression analysis service."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.logging import get_logger

from app.modules.inspector.crud import get_execution_trace
from app.modules.inspector.models import TbExecutionTrace
from app.modules.inspector.regression.schemas import (
    RegressionAnalysisRequest,
    RegressionAnalysisResult,
    StageCompareResponse,
    StageMetrics,
    StageRegressionReport,
)

logger = get_logger(__name__)


class RegressionService:
    """Service for performing regression analysis on execution traces."""

    def __init__(self):
        self.analysis_registry: Dict[str, RegressionAnalysisResult] = {}

    async def analyze_stage_regression(
        self, request: RegressionAnalysisRequest
    ) -> RegressionAnalysisResult:
        """
        Perform stage-level regression analysis between two traces.
        """
        analysis_id = f"reg_{int(time.time())}"
        time.time()

        # Initialize analysis result
        result = RegressionAnalysisResult(
            analysis_id=analysis_id,
            type=request.type,
            baseline_trace_id=request.baseline_trace_id,
            comparison_trace_id=request.comparison_trace_id,
            started_at=datetime.now(),
            status="running",
        )

        try:
            # Get baseline and comparison traces
            baseline_trace = get_execution_trace(None, request.baseline_trace_id)
            comparison_trace = get_execution_trace(None, request.comparison_trace_id)

            if not baseline_trace or not comparison_trace:
                raise ValueError("One or both traces not found")

            # Parse stage inputs and outputs
            baseline_stages = self._parse_stages_from_trace(baseline_trace)
            comparison_stages = self._parse_stages_from_trace(comparison_trace)

            # Compare each stage
            stage_reports = []
            for stage_name in request.parameters.get("stages", baseline_stages.keys()):
                if stage_name in baseline_stages and stage_name in comparison_stages:
                    report = await self._compare_stages(
                        stage_name,
                        baseline_stages[stage_name],
                        comparison_stages[stage_name],
                    )
                    stage_reports.append(report)

            # Calculate overall metrics
            overall_score = self._calculate_overall_regression_score(stage_reports)
            significant_changes = len(
                [r for r in stage_reports if r.regression_score > 70]
            )
            critical_issues = self._identify_critical_issues(stage_reports)

            # Update result
            result.stage_reports = stage_reports
            result.overall_regression_score = overall_score
            result.significant_changes = significant_changes
            result.critical_issues = critical_issues
            result.status = "completed"
            result.completed_at = datetime.now()

            # Generate summary
            result.summary = self._generate_summary(result)
            result.recommendations = self._generate_recommendations(stage_reports)

            # Store in registry
            self.analysis_registry[analysis_id] = result

            logger.info(f"Regression analysis completed: {analysis_id}")

        except Exception as e:
            result.status = "failed"
            result.critical_issues = [f"Analysis failed: {str(e)}"]
            logger.error(f"Regression analysis failed: {analysis_id} - {str(e)}")

        return result

    async def compare_stages_direct(
        self,
        baseline_trace_id: str,
        comparison_trace_id: str,
        stages: Optional[List[str]] = None,
    ) -> StageCompareResponse:
        """
        Direct comparison of two traces' stages.
        """
        # Get traces
        baseline_trace = get_execution_trace(None, baseline_trace_id)
        comparison_trace = get_execution_trace(None, comparison_trace_id)

        if not baseline_trace or not comparison_trace:
            raise ValueError("One or both traces not found")

        # Parse stages
        baseline_stages = self._parse_stages_from_trace(baseline_trace)
        comparison_stages = self._parse_stages_from_trace(comparison_trace)

        # Compare stages
        stage_differences = {}
        regression_scores = {}

        for stage_name in stages or baseline_stages.keys():
            if stage_name in baseline_stages and stage_name in comparison_stages:
                baseline = baseline_stages[stage_name]
                comparison = comparison_stages[stage_name]

                # Calculate differences
                duration_diff = comparison.get("duration_ms", 0) - baseline.get(
                    "duration_ms", 0
                )
                status_changed = baseline.get("status") != comparison.get("status")

                stage_differences[stage_name] = {
                    "duration_difference_ms": duration_diff,
                    "status_changed": status_changed,
                    "input_size_difference": self._calculate_size_difference(
                        baseline.get("input"), comparison.get("input")
                    ),
                    "output_size_difference": self._calculate_size_difference(
                        baseline.get("output"), comparison.get("output")
                    ),
                    "reference_count_difference": (
                        comparison.get("reference_count", 0)
                        - baseline.get("reference_count", 0)
                    ),
                    "baseline_metrics": self._extract_stage_metrics(baseline),
                    "comparison_metrics": self._extract_stage_metrics(comparison),
                }

                # Calculate regression score for this stage
                regression_scores[stage_name] = self._calculate_stage_regression_score(
                    baseline, comparison
                )

        # Generate overall assessment
        overall_assessment = self._generate_overall_assessment(regression_scores)

        return StageCompareResponse(
            baseline_trace=baseline_trace.model_dump(),
            comparison_trace=comparison_trace.model_dump(),
            stage_differences=stage_differences,
            regression_scores=regression_scores,
            overall_assessment=overall_assessment,
        )

    def _parse_stages_from_trace(self, trace: TbExecutionTrace) -> Dict[str, Any]:
        """Parse stage inputs and outputs from trace data."""
        stages = {}

        # Parse stage inputs
        if trace.stage_inputs:
            for stage_input in trace.stage_inputs:
                stage_name = stage_input.get("stage", "unknown")
                stages[stage_name] = {
                    "input": stage_input,
                    "input_size": len(str(stage_input).encode()),
                }

        # Parse stage outputs
        if trace.stage_outputs:
            for stage_output in trace.stage_outputs:
                stage_name = stage_output.get("stage", "unknown")
                if stage_name in stages:
                    stages[stage_name].update(
                        {
                            "output": stage_output,
                            "output_size": len(str(stage_output).encode()),
                            "duration_ms": stage_output.get("duration_ms", 0),
                            "status": stage_output.get("diagnostics", {}).get(
                                "status", "unknown"
                            ),
                            "reference_count": len(stage_output.get("references", [])),
                        }
                    )
                else:
                    stages[stage_name] = {
                        "output": stage_output,
                        "output_size": len(str(stage_output).encode()),
                        "duration_ms": stage_output.get("duration_ms", 0),
                        "status": stage_output.get("diagnostics", {}).get(
                            "status", "unknown"
                        ),
                        "reference_count": len(stage_output.get("references", [])),
                    }

        return stages

    async def _compare_stages(
        self,
        stage_name: str,
        baseline_data: Dict[str, Any],
        comparison_data: Dict[str, Any],
    ) -> StageRegressionReport:
        """Compare two stages and generate a regression report."""
        # Extract metrics
        baseline_metrics = self._extract_stage_metrics(baseline_data)
        current_metrics = self._extract_stage_metrics(comparison_data)

        # Calculate differences
        differences = {
            "duration_ms": current_metrics.duration_ms - baseline_metrics.duration_ms,
            "reference_count": current_metrics.reference_count
            - baseline_metrics.reference_count,
            "status_changed": baseline_metrics.status != current_metrics.status,
        }

        # Calculate regression score
        regression_score = self._calculate_stage_regression_score(
            baseline_data, comparison_data
        )

        # Identify issues
        issues = []
        recommendations = []

        if regression_score > 80:
            issues.append(f"Significant regression detected in {stage_name}")
            if differences["duration_ms"] > 1000:
                recommendations.append(f"Performance degraded in {stage_name}")
            if current_metrics.status == "error":
                recommendations.append(f"Fix errors in {stage_name}")

        return StageRegressionReport(
            stage_name=stage_name,
            baseline_metrics=baseline_metrics,
            current_metrics=current_metrics,
            differences=differences,
            regression_score=regression_score,
            issues=issues,
            recommendations=recommendations,
        )

    def _extract_stage_metrics(self, stage_data: Dict[str, Any]) -> StageMetrics:
        """Extract metrics from stage data."""
        return StageMetrics(
            stage_name=stage_data.get("stage", "unknown"),
            duration_ms=stage_data.get("duration_ms", 0),
            status=stage_data.get("status", "unknown"),
            input_size=stage_data.get("input_size", 0),
            output_size=stage_data.get("output_size", 0),
            reference_count=stage_data.get("reference_count", 0),
            error_count=len(
                stage_data.get("output", {}).get("diagnostics", {}).get("errors", [])
            ),
            warning_count=len(
                stage_data.get("output", {}).get("diagnostics", {}).get("warnings", [])
            ),
        )

    def _calculate_stage_regression_score(
        self, baseline_data: Dict[str, Any], comparison_data: Dict[str, Any]
    ) -> int:
        """Calculate regression score for a stage (0-100)."""
        score = 100

        # Check for errors
        baseline_errors = len(
            baseline_data.get("output", {}).get("diagnostics", {}).get("errors", [])
        )
        comparison_errors = len(
            comparison_data.get("output", {}).get("diagnostics", {}).get("errors", [])
        )

        if baseline_errors == 0 and comparison_errors > 0:
            score -= min(50, comparison_errors * 10)

        # Check for status changes
        baseline_status = baseline_data.get("status", "unknown")
        comparison_status = comparison_data.get("status", "unknown")

        if baseline_status != comparison_status:
            if comparison_status == "error":
                score -= 30
            elif comparison_status == "warning":
                score -= 10

        # Check duration changes
        baseline_duration = baseline_data.get("duration_ms", 0)
        comparison_duration = comparison_data.get("duration_ms", 0)

        if baseline_duration > 0:
            duration_change = (
                abs(comparison_duration - baseline_duration) / baseline_duration
            )
            if duration_change > 0.5:  # 50% change
                score -= min(20, int(duration_change * 40))

        return max(0, score)

    def _calculate_overall_regression_score(
        self, stage_reports: List[StageRegressionReport]
    ) -> int:
        """Calculate overall regression score from stage reports."""
        if not stage_reports:
            return 100

        total_score = sum(report.regression_score for report in stage_reports)
        return int(total_score / len(stage_reports))

    def _identify_critical_issues(
        self, stage_reports: List[StageRegressionReport]
    ) -> List[str]:
        """Identify critical issues from stage reports."""
        issues = []

        for report in stage_reports:
            if report.regression_score > 90:
                issues.append(f"Critical regression in {report.stage_name}")

            for issue in report.issues:
                if "critical" in issue.lower() or "error" in issue.lower():
                    issues.append(issue)

        return issues

    def _calculate_size_difference(self, baseline: Any, comparison: Any) -> int:
        """Calculate size difference between two data structures."""
        baseline_size = len(str(baseline).encode()) if baseline else 0
        comparison_size = len(str(comparison).encode()) if comparison else 0
        return comparison_size - baseline_size

    def _generate_summary(self, result: RegressionAnalysisResult) -> str:
        """Generate a summary of the analysis."""
        if result.status == "failed":
            return "Analysis failed due to errors"

        significant_changes = result.significant_changes
        total_stages = len(result.stage_reports)

        if significant_changes == 0:
            return f"No significant changes detected across {total_stages} stages"
        elif significant_changes == 1:
            return f"1 stage showed significant changes out of {total_stages}"
        else:
            return f"{significant_changes} stages showed significant changes out of {total_stages}"

    def _generate_recommendations(
        self, stage_reports: List[StageRegressionReport]
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        for report in stage_reports:
            recommendations.extend(report.recommendations)

        # Add general recommendations
        if stage_reports and any(r.regression_score < 70 for r in stage_reports):
            recommendations.append(
                "Consider investigating the root cause of performance degradation"
            )

        return list(set(recommendations))  # Remove duplicates

    def _generate_overall_assessment(self, regression_scores: Dict[str, int]) -> str:
        """Generate overall assessment from regression scores."""
        if not regression_scores:
            return "No data available for comparison"

        avg_score = sum(regression_scores.values()) / len(regression_scores)
        high_regression_count = sum(
            1 for score in regression_scores.values() if score > 70
        )

        if avg_score > 80:
            return (
                f"Significant regression detected across {high_regression_count} stages"
            )
        elif avg_score > 60:
            return f"Moderate regression detected in {high_regression_count} stages"
        else:
            return "No significant regression detected"


# Global service instance
regression_service = RegressionService()

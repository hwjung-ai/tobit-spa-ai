"""CRUD operations for regression analysis."""

from typing import Optional

from app.modules.inspector.regression.service import regression_service


class RegressionCRUD:
    """CRUD operations for regression analysis."""

    @staticmethod
    def get_regression_analysis(analysis_id: str):
        """Get regression analysis by ID."""
        return regression_service.analysis_registry.get(analysis_id)

    @staticmethod
    async def compare_stage_traces(
        baseline_trace_id: str, comparison_trace_id: str, stages: Optional[list] = None
    ):
        """Compare two traces' stages."""
        return await regression_service.compare_stages_direct(
            baseline_trace_id, comparison_trace_id, stages
        )


# Global CRUD instance
regression_crud = RegressionCRUD()

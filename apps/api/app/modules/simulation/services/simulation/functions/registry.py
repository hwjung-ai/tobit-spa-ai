"""
SIM Function Library - Function Registry

Central registry for all simulation functions.
Provides lookup, filtering, and validation capabilities.
"""

from __future__ import annotations

from typing import Any

from app.modules.simulation.services.simulation.functions.base import (
    FunctionCategory,
    FunctionComplexity,
    FunctionMetadata,
    SimulationFunction,
)
from app.modules.simulation.services.simulation.functions.domain_functions import (
    AvailabilityModel,
    CapacityPlanning,
    CloudCostModel,
    FailureCascading,
    ResponseTimeDecomposition,
    TCOCalculator,
    UtilizationImpact,
)
from app.modules.simulation.services.simulation.functions.ml_functions import (
    ARIMASurrogate,
    GRUSurrogate,
    LSTMSurrogate,
    ProphetSurrogate,
    RandomForestSurrogate,
    SVRSurrogate,
)
from app.modules.simulation.services.simulation.functions.rule_functions import (
    ErlangCRule,
    LinearWeightRule,
    LittleLawRule,
    PolynomialRule,
    ThresholdRule,
)
from app.modules.simulation.services.simulation.functions.stat_functions import (
    ExponentialMovingAverage,
    LinearRegressionForecast,
    PercentileForecast,
    PolynomialRegressionForecast,
    SimpleMovingAverage,
    StandardDeviationImpact,
)

# =============================================================================
# Function Registry
# =============================================================================

class FunctionRegistry:
    """
    Central registry for all simulation functions.

    Provides:
    - Function lookup by ID
    - Filtering by category/complexity/tags
    - Function metadata listing
    - Function instantiation
    """

    _functions: dict[str, type[SimulationFunction]] = {}
    _initialized = False

    @classmethod
    def _initialize(cls) -> None:
        """Initialize the registry with all available functions."""
        if cls._initialized:
            return

        # Rule Functions
        cls._register(LinearWeightRule)
        cls._register(PolynomialRule)
        cls._register(ThresholdRule)
        cls._register(LittleLawRule)
        cls._register(ErlangCRule)

        # Statistical Functions
        cls._register(SimpleMovingAverage)
        cls._register(ExponentialMovingAverage)
        cls._register(LinearRegressionForecast)
        cls._register(PolynomialRegressionForecast)
        cls._register(StandardDeviationImpact)
        cls._register(PercentileForecast)

        # ML Functions
        cls._register(ARIMASurrogate)
        cls._register(ProphetSurrogate)
        cls._register(SVRSurrogate)
        cls._register(RandomForestSurrogate)
        cls._register(LSTMSurrogate)
        cls._register(GRUSurrogate)

        # Domain Functions
        cls._register(ResponseTimeDecomposition)
        cls._register(UtilizationImpact)
        cls._register(AvailabilityModel)
        cls._register(FailureCascading)
        cls._register(CloudCostModel)
        cls._register(TCOCalculator)
        cls._register(CapacityPlanning)

        cls._initialized = True

    @classmethod
    def _register(cls, function_class: type[SimulationFunction]) -> None:
        """Register a function class."""
        if not hasattr(function_class, "metadata"):
            raise ValueError(f"Function class {function_class.__name__} must have metadata attribute")

        function_id = function_class.metadata.id
        cls._functions[function_id] = function_class

    @classmethod
    def get(cls, function_id: str) -> SimulationFunction | None:
        """Get a function instance by ID."""
        cls._initialize()
        function_class = cls._functions.get(function_id)
        if function_class:
            return function_class()
        return None

    @classmethod
    def get_metadata(cls, function_id: str) -> FunctionMetadata | None:
        """Get function metadata without instantiating."""
        cls._initialize()
        function_class = cls._functions.get(function_id)
        if function_class:
            return function_class.metadata
        return None

    @classmethod
    def list_all(cls) -> list[FunctionMetadata]:
        """List all available function metadata."""
        cls._initialize()
        return [func.metadata for func in cls._functions.values()]

    @classmethod
    def list_by_category(cls, category: FunctionCategory) -> list[FunctionMetadata]:
        """List functions by category."""
        cls._initialize()
        return [
            func.metadata
            for func in cls._functions.values()
            if func.metadata.category == category
        ]

    @classmethod
    def list_by_complexity(cls, complexity: FunctionComplexity) -> list[FunctionMetadata]:
        """List functions by complexity level."""
        cls._initialize()
        return [
            func.metadata
            for func in cls._functions.values()
            if func.metadata.complexity == complexity
        ]

    @classmethod
    def list_by_tags(cls, tags: list[str]) -> list[FunctionMetadata]:
        """List functions that match any of the given tags."""
        cls._initialize()
        result = []
        for func in cls._functions.values():
            func_tags = func.metadata.tags
            if any(tag.lower() in [t.lower() for t in func_tags] for tag in tags):
                result.append(func.metadata)
        return result

    @classmethod
    def search(cls, query: str) -> list[FunctionMetadata]:
        """Search functions by name, description, or ID."""
        cls._initialize()
        query_lower = query.lower()
        result = []
        for func in cls._functions.values():
            meta = func.metadata
            if (
                query_lower in meta.id.lower()
                or query_lower in meta.name.lower()
                or query_lower in meta.description.lower()
            ):
                result.append(meta)
        return result

    @classmethod
    def get_categories(cls) -> list[FunctionCategory]:
        """Get all available categories."""
        return [c for c in FunctionCategory]

    @classmethod
    def get_complexities(cls) -> list[FunctionComplexity]:
        """Get all available complexity levels."""
        return [c for c in FunctionComplexity]

    @classmethod
    def get_all_tags(cls) -> list[str]:
        """Get all unique tags across all functions."""
        cls._initialize()
        tags_set = set()
        for func in cls._functions.values():
            tags_set.update(func.metadata.tags)
        return sorted(list(tags_set))

    @classmethod
    def execute_function(
        cls,
        function_id: str,
        *,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, float], float, dict[str, Any]]:
        """
        Execute a function by ID.

        Args:
            function_id: The function ID to execute
            baseline: Baseline KPI values
            assumptions: Input assumptions
            context: Optional context

        Returns:
            (outputs, confidence, debug_info)
        """
        function = cls.get(function_id)
        if not function:
            return {}, 0.0, {"error": f"Function not found: {function_id}"}

        # Validate inputs
        validation_errors = function.validate_inputs(baseline, assumptions)
        if validation_errors:
            return {}, 0.0, {"error": "Validation failed", "details": validation_errors}

        # Execute function
        try:
            return function.execute(baseline=baseline, assumptions=assumptions, context=context)
        except Exception as e:
            return {}, 0.0, {"error": f"Execution failed: {str(e)}"}


# =============================================================================
# Convenience Functions
# =============================================================================

def list_functions(
    category: FunctionCategory | None = None,
    complexity: FunctionComplexity | None = None,
    tags: list[str] | None = None,
    search: str | None = None,
) -> list[FunctionMetadata]:
    """
    List functions with optional filtering.

    Args:
        category: Filter by category
        complexity: Filter by complexity
        tags: Filter by tags (any match)
        search: Search in name/description/id

    Returns:
        List of matching function metadata
    """
    results = FunctionRegistry.list_all()

    if category:
        results = [r for r in results if r.category == category]

    if complexity:
        results = [r for r in results if r.complexity == complexity]

    if tags:
        results = [
            r for r in results
            if any(tag.lower() in [t.lower() for t in r.tags] for tag in tags)
        ]

    if search:
        search_lower = search.lower()
        results = [
            r for r in results
            if search_lower in r.id.lower()
            or search_lower in r.name.lower()
            or search_lower in r.description.lower()
        ]

    return results


def get_function_info(function_id: str) -> dict[str, Any] | None:
    """
    Get detailed information about a function.

    Returns:
        Dict with function metadata including parameters and outputs
    """
    meta = FunctionRegistry.get_metadata(function_id)
    if not meta:
        return None

    return {
        "id": meta.id,
        "name": meta.name,
        "category": meta.category.value,
        "complexity": meta.complexity.value,
        "description": meta.description,
        "confidence": meta.confidence,
        "tags": meta.tags,
        "assumptions": meta.assumptions,
        "references": meta.references,
        "version": meta.version,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "default": p.default,
                "min": p.min,
                "max": p.max,
                "step": p.step,
                "description": p.description,
                "unit": p.unit,
                "required": p.required,
            }
            for p in meta.parameters
        ],
        "outputs": [
            {
                "name": o.name,
                "unit": o.unit,
                "description": o.description,
            }
            for o in meta.outputs
        ],
    }


def execute_simulation(
    function_id: str,
    baseline: dict[str, float],
    assumptions: dict[str, float],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute a simulation function and return formatted result.

    Returns:
        Dict with outputs, confidence, and debug info
    """
    outputs, confidence, debug_info = FunctionRegistry.execute_function(
        function_id=function_id,
        baseline=baseline,
        assumptions=assumptions,
        context=context,
    )

    return {
        "function_id": function_id,
        "outputs": outputs,
        "confidence": confidence,
        "debug_info": debug_info,
        "success": len(debug_info.get("error", "")) == 0,
    }


# =============================================================================
# Strategy Adapters (Backward Compatibility)
# =============================================================================

def get_strategy_function(strategy: str) -> SimulationFunction:
    """
    Get a function instance for a legacy strategy name.

    Maps old strategy names to new function IDs for backward compatibility.
    """
    mapping = {
        "rule": "rule_linear_weight",
        "stat": "stat_ema",
        "ml": "ml_random_forest_surrogate",
        "dl": "ml_lstm_surrogate",
    }

    function_id = mapping.get(strategy, "rule_linear_weight")
    function = FunctionRegistry.get(function_id)

    if not function:
        # Fallback to linear weight rule
        function = LinearWeightRule()

    return function
